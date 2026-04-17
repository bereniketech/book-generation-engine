"""Pipeline runner. Orchestrates all engine stages for a single job."""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from worker.clients.image_client import ImageClient
from worker.clients.llm_client import LLMClient
from worker.clients.notebooklm_client import NotebookLMClient
from worker.memory.store import FictionMemory, NonFictionMemory
from worker.pipeline.assembly import (
    CoverEngine,
    FinalAssemblyEngine,
    FormattingEngine,
    PackagingEngine,
)
from worker.pipeline.base import JobConfig
from worker.pipeline.fiction_path import (
    CharacterEngine,
    ConceptEngine,
    ConflictEngine,
    EndingEngine,
    StoryMemoryInitEngine,
    StructureEngine,
    ThemeEngine,
)
from worker.pipeline.generation import (
    ChapterGeneratorEngine,
    ContinuityEngine,
    QAEngine,
    StyleEnforcerEngine,
    chapter_passed,
)
from worker.pipeline.non_fiction_path import (
    ContentMapEngine,
    EvidenceEngine,
    FrameworkEngine,
    KnowledgeMemoryInitEngine,
    PromiseEngine,
    ResearchStep,
)
from worker.pipeline.shared_core import (
    AudienceEngine,
    ContentBlueprintSelectorEngine,
    EntryGateEngine,
    IntentEngine,
    PositioningEngine,
)
from worker.services import storage_service

logger = logging.getLogger(__name__)

MAX_CHAPTER_RETRIES = 2

_SHARED_CORE_ENGINES = [
    EntryGateEngine,
    IntentEngine,
    AudienceEngine,
    PositioningEngine,
    ContentBlueprintSelectorEngine,
]

_FICTION_PATH_ENGINES = [
    ConceptEngine,
    ThemeEngine,
    CharacterEngine,
    ConflictEngine,
    StructureEngine,
    EndingEngine,
    StoryMemoryInitEngine,
]

_NON_FICTION_PATH_ENGINES = [
    PromiseEngine,
    FrameworkEngine,
    ContentMapEngine,
    EvidenceEngine,
    KnowledgeMemoryInitEngine,
]

_CHAPTER_ENGINES = [
    ChapterGeneratorEngine,
    ContinuityEngine,
    QAEngine,
    StyleEnforcerEngine,
]


class PipelineRunner:
    """Runs the full book generation pipeline for one job."""

    def __init__(
        self,
        config: JobConfig,
        supabase: Any,
        progress_callback: Callable[[dict], None],
    ) -> None:
        self.config = config
        self.supabase = supabase
        self.progress = progress_callback

        self.llm = LLMClient(
            provider=config.llm_provider,
            model=config.llm_model,
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
        )
        self.image_client = ImageClient(
            provider=config.image_provider,
            api_key=config.image_api_key,
        )
        self.notebooklm = NotebookLMClient(api_key=config.llm_api_key)  # uses Google key

        if config.mode == "fiction":
            self.memory: FictionMemory | NonFictionMemory = FictionMemory(config.job_id)
        else:
            self.memory = NonFictionMemory(config.job_id)

    def run(self) -> None:
        """Execute the full pipeline. Updates Supabase at each stage."""
        ctx: dict[str, Any] = {}

        # --- Shared Core ---
        self._emit("planning", "entry_gate", 0)
        for engine_cls in _SHARED_CORE_ENGINES:
            engine = engine_cls(llm=self.llm, memory=self.memory, config=self.config)
            ctx = engine.run(ctx)
        self._update_job_status("planning")

        # --- Branch ---
        if ctx["branch"] == "fiction":
            ctx = self._run_fiction_path(ctx)
        else:
            ctx = self._run_non_fiction_path(ctx)

        # --- Chapter Generation Loop ---
        chapters_blueprint = self._get_chapters_blueprint(ctx)
        locked_chapters: list[dict] = []
        total = len(chapters_blueprint)

        for i, ch_brief in enumerate(chapters_blueprint):
            ctx["chapter_index"] = i
            ctx["chapter_brief"] = ch_brief
            ctx["memory_snapshot"] = self.memory.snapshot()

            locked = False
            for attempt in range(MAX_CHAPTER_RETRIES + 1):
                self._emit("generating", f"chapter_{i}", i / total * 100)
                for engine_cls in _CHAPTER_ENGINES:
                    engine = engine_cls(llm=self.llm, memory=self.memory, config=self.config)
                    ctx = engine.run(ctx)

                if chapter_passed(ctx):
                    self.memory.lock_chapter(i)
                    ch_record = {
                        "index": i,
                        "title": ch_brief.get("title", f"Chapter {i + 1}"),
                        "content": ctx["generated_content"],
                    }
                    locked_chapters.append(ch_record)
                    self._save_chapter(
                        i, ch_record["title"], ctx["generated_content"], "locked"
                    )
                    locked = True
                    break
                elif attempt < MAX_CHAPTER_RETRIES:
                    logger.warning(
                        "Chapter %d failed QA (attempt %d) — retrying", i, attempt + 1
                    )
                    ctx.pop("generated_content", None)

            if not locked:
                self._save_chapter(
                    i,
                    ch_brief.get("title", f"Chapter {i + 1}"),
                    ctx.get("generated_content", ""),
                    "qa_failed",
                )
                self._update_job_status("paused")
                self._emit("paused", f"chapter_{i}_qa_failed", i / total * 100)
                return

        ctx["locked_chapters"] = locked_chapters

        # --- Assembly ---
        self._emit("assembling", "final_assembly", 90)
        self._update_job_status("assembling")
        for engine_cls in [FinalAssemblyEngine, PackagingEngine]:
            engine = engine_cls(llm=self.llm, memory=self.memory, config=self.config)
            ctx = engine.run(ctx)

        cover_engine = CoverEngine(
            llm=self.llm,
            memory=self.memory,
            config=self.config,
            image_client=self.image_client,
        )
        ctx = cover_engine.run(ctx)

        formatting_engine = FormattingEngine(
            llm=self.llm, memory=self.memory, config=self.config
        )
        ctx = formatting_engine.run(ctx)

        # --- Upload artifacts ---
        bundle_path = storage_service.upload_bytes(
            self.supabase,
            self.config.job_id,
            "bundle.zip",
            ctx["bundle_bytes"],
            "application/zip",
        )
        download_url = storage_service.get_signed_url(self.supabase, bundle_path)

        self._update_job_status("complete")
        self._emit("complete", "complete", 100, download_url=download_url)
        logger.info("Job %s complete. Bundle: %s", self.config.job_id, bundle_path)

    def _run_fiction_path(self, ctx: dict) -> dict:
        for engine_cls in _FICTION_PATH_ENGINES:
            engine = engine_cls(llm=self.llm, memory=self.memory, config=self.config)
            ctx = engine.run(ctx)
        return ctx

    def _run_non_fiction_path(self, ctx: dict) -> dict:
        assert isinstance(self.memory, NonFictionMemory)
        research = ResearchStep(
            notebooklm_client=self.notebooklm,
            llm=self.llm,
            config=self.config,
            memory=self.memory,
        )
        ctx = research.run(ctx)
        for engine_cls in _NON_FICTION_PATH_ENGINES:
            engine = engine_cls(llm=self.llm, memory=self.memory, config=self.config)
            ctx = engine.run(ctx)
        return ctx

    def _get_chapters_blueprint(self, ctx: dict) -> list[dict]:
        """Extract per-chapter briefs from planning context."""
        if ctx.get("branch") == "fiction":
            structure = ctx.get("structure", {})
            chapters = []
            for act in structure.get("acts", []):
                chapters.extend(act.get("chapters", []))
            if not chapters:
                chapters = [
                    {"index": i, "title": f"Chapter {i + 1}", "beats": []}
                    for i in range(self.config.target_chapters)
                ]
            return chapters
        else:
            content_map = ctx.get("content_map", {})
            chapters = content_map.get("chapters", [])
            if not chapters:
                chapters = [
                    {"index": i, "title": f"Chapter {i + 1}", "key_points": []}
                    for i in range(self.config.target_chapters)
                ]
            return chapters

    def _emit(
        self, status: str, step: str, progress_pct: float, **extra: Any
    ) -> None:
        self.progress(
            {
                "job_id": self.config.job_id,
                "status": status,
                "step": step,
                "progress": progress_pct,
                **extra,
            }
        )

    def _update_job_status(self, status: str) -> None:
        (
            self.supabase.table("jobs")
            .update({"status": status})
            .eq("id", self.config.job_id)
            .execute()
        )

    def _save_chapter(
        self, index: int, title: str, content: str, status: str
    ) -> None:
        self.supabase.table("chapters").upsert(
            {
                "job_id": self.config.job_id,
                "index": index,
                "content": content,
                "status": status,
                "memory_snapshot": self.memory.snapshot(),
            }
        ).execute()
