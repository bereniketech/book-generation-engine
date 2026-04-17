---
task: 010
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: ai-ml-expert
depends_on: [009]
---

# Task 010: Final Assembly, Packaging, Cover, and Formatting Engines

## Skills
- .kit/skills/data-science-ml/ai-engineer/SKILL.md
- .kit/skills/languages/python-patterns/SKILL.md
- .kit/skills/research-docs/copy-editing/SKILL.md
- .kit/skills/research-docs/avoid-ai-writing/SKILL.md

## Agents
- @ai-ml-expert
- @image-creation-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else.

---

## Objective

Implement `worker/pipeline/assembly.py` with 4 engines: Final Assembly (concatenate chapters), Packaging (description + metadata JSON), Cover (cover-brief + cover.jpg), and Formatting (EPUB + PDF). Also implement `worker/services/storage_service.py` for Supabase Storage uploads.

---

## Files

### Create
| File | Purpose |
|------|---------|
| `worker/pipeline/assembly.py` | 4 assembly engines |
| `worker/services/__init__.py` | Empty |
| `worker/services/storage_service.py` | Supabase Storage upload helper |
| `tests/unit/test_assembly.py` | Unit tests with stub LLM + ImageClient + storage |

---

## Dependencies

```bash
# ebooklib and reportlab already in pyproject.toml.
# No new packages.
```

---

## Code Templates

### `worker/services/storage_service.py` (create this file exactly)
```python
"""Supabase Storage upload helper for worker processes."""
from __future__ import annotations

import logging
from pathlib import Path

from supabase import Client

logger = logging.getLogger(__name__)

BUCKET = "book-artifacts"


def upload_bytes(supabase: Client, job_id: str, filename: str, data: bytes, content_type: str) -> str:
    """Upload bytes to Supabase Storage. Returns storage path."""
    path = f"{job_id}/{filename}"
    supabase.storage.from_(BUCKET).upload(
        path=path,
        file=data,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    logger.info("Uploaded %s (%d bytes) for job %s", filename, len(data), job_id)
    return path


def get_signed_url(supabase: Client, path: str, expires_in: int = 604800) -> str:
    """Return a signed URL valid for expires_in seconds (default 7 days)."""
    response = supabase.storage.from_(BUCKET).create_signed_url(path, expires_in)
    return response["signedURL"]
```

### `worker/pipeline/assembly.py` (create this file exactly)
```python
"""Final assembly, packaging, cover, and formatting engines."""
from __future__ import annotations

import io
import json
import logging
import zipfile
from typing import Any

from worker.clients.image_client import ImageClient
from worker.pipeline.base import BaseEngine

logger = logging.getLogger(__name__)

_SYSTEM = "You are a professional book publisher. Output JSON only where specified."
_DESCRIPTION_SYSTEM = (
    "You are a professional book marketing copywriter.\n"
    "Rules for book descriptions:\n"
    "- Lead with the reader's problem or desire — not the author's background.\n"
    "- Every claim must answer 'so what?' with a concrete benefit.\n"
    "- Use specific, concrete language. No vague adjectives ('amazing', 'powerful', 'incredible').\n"
    "- No AI-isms: 'leverage', 'robust', 'seamless', 'cutting-edge', 'delve into', 'tapestry', 'embark'.\n"
    "- No filler openers: 'In today's world', 'Are you ready to', 'This book will change your life'.\n"
    "- Vary sentence length. Short punchy sentences create urgency.\n"
    "- End with a clear call to action or irresistible hook.\n"
    "Output clean prose only — no headings, no bullets unless asked."
)


class FinalAssemblyEngine(BaseEngine):
    """Concatenates all locked chapters into manuscript_final.txt."""
    name = "final_assembly"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        chapters: list[dict] = context.get("locked_chapters", [])
        parts = []
        for ch in sorted(chapters, key=lambda c: c["index"]):
            parts.append(f"# Chapter {ch['index'] + 1}: {ch.get('title', '')}\n\n{ch['content']}\n")
        manuscript = "\n\n".join(parts)
        context["manuscript_text"] = manuscript
        logger.info("[FinalAssembly] Assembled %d chapters for job %s", len(chapters), self.config.job_id)
        return context


class PackagingEngine(BaseEngine):
    """Generates book description and KDP metadata via LLM."""
    name = "packaging_engine"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        manuscript_excerpt = context.get("manuscript_text", "")[:3000]
        prompt = (
            f"Book title: '{self.config.title}'. Mode: {self.config.mode}. Audience: {self.config.audience}.\n"
            f"Manuscript excerpt:\n{manuscript_excerpt}\n\n"
            "Generate KDP metadata as JSON. The 'description' field must be compelling marketing copy "
            "written for Amazon KDP — specific, benefit-driven, no AI-isms, no filler openers. "
            "Format: "
            '{"title": "...", "subtitle": "...", "description": "...", '
            '"keywords": ["kw1","kw2","kw3","kw4","kw5","kw6","kw7"], '
            '"categories": ["cat1", "cat2"]}'
        )
        raw = self.llm.complete(prompt, _DESCRIPTION_SYSTEM)
        try:
            metadata = json.loads(raw)
        except json.JSONDecodeError:
            metadata = {
                "title": self.config.title,
                "subtitle": "",
                "description": raw,
                "keywords": [],
                "categories": [],
            }
        context["metadata"] = metadata
        context["description_text"] = metadata.get("description", "")
        return context


class CoverEngine(BaseEngine):
    """Generates cover brief text and cover image bytes."""
    name = "cover_engine"

    def __init__(self, *args: Any, image_client: ImageClient, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.image_client = image_client

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        metadata = context.get("metadata", {})

        # Step 1: Generate cover brief via LLM (art-director pass)
        brief_prompt = (
            f"Book: '{self.config.title}'. Subtitle: '{metadata.get('subtitle', '')}'.\n"
            f"Description: {metadata.get('description', '')[:500]}.\n"
            "Write a detailed cover design brief for a human designer. "
            "Include: dominant colors, imagery, typography style, mood, and composition."
        )
        cover_brief = self.llm.complete(brief_prompt, "You are a book cover art director.")
        context["cover_brief"] = cover_brief

        # Step 2: Human-in-the-loop — pause for @image-creation-expert review
        # The runner checks context["cover_brief_approved"] before proceeding.
        # If not set, it saves state to Supabase, emits status "awaiting_cover_approval",
        # and halts. The dashboard shows the brief and an Approve / Edit + Approve button.
        # On approval, the runner resumes with context["cover_brief_approved"] = True
        # and optionally context["cover_brief_revised"] containing the edited brief.
        if not context.get("cover_brief_approved", False):
            context["status"] = "awaiting_cover_approval"
            logger.info("[CoverEngine] Awaiting cover brief approval for job %s", self.config.job_id)
            return context

        # Use revised brief if the user edited it during review
        approved_brief = context.get("cover_brief_revised", cover_brief)
        context["cover_brief"] = approved_brief

        # Step 3: Generate cover image from approved brief
        image_prompt = (
            f"Professional book cover for '{self.config.title}'. "
            f"Genre/mode: {self.config.mode}. "
            f"Style: {self.config.tone}. "
            f"Design direction: {approved_brief[:300]}. "
            "High quality, KDP-ready. Portrait orientation 1024x1536."
        )
        cover_bytes = self.image_client.generate(image_prompt, width=1024, height=1536)
        context["cover_bytes"] = cover_bytes
        logger.info("[CoverEngine] Cover generated for job %s (%d bytes)", self.config.job_id, len(cover_bytes))
        return context


class FormattingEngine(BaseEngine):
    """Produces EPUB and PDF from manuscript text, then creates a zip bundle."""
    name = "formatting_engine"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        manuscript = context.get("manuscript_text", "")
        chapters_list: list[dict] = context.get("locked_chapters", [])
        metadata: dict = context.get("metadata", {})
        title = metadata.get("title", self.config.title)

        epub_bytes = self._make_epub(title, manuscript, chapters_list, metadata)
        pdf_bytes = self._make_pdf(title, manuscript)
        bundle_bytes = self._make_bundle(
            epub_bytes=epub_bytes,
            pdf_bytes=pdf_bytes,
            cover_bytes=context.get("cover_bytes", b""),
            cover_brief=context.get("cover_brief", ""),
            description=context.get("description_text", ""),
            metadata_dict=metadata,
        )
        context["epub_bytes"] = epub_bytes
        context["pdf_bytes"] = pdf_bytes
        context["bundle_bytes"] = bundle_bytes
        logger.info("[FormattingEngine] Bundle created (%d bytes) for job %s", len(bundle_bytes), self.config.job_id)
        return context

    def _make_epub(self, title: str, manuscript: str, chapters_list: list, metadata: dict) -> bytes:
        import ebooklib
        from ebooklib import epub

        book = epub.EpubBook()
        book.set_title(title)
        book.set_language("en")

        chapter_items = []
        for ch_data in sorted(chapters_list, key=lambda c: c["index"]):
            ch = epub.EpubHtml(
                title=ch_data.get("title", f"Chapter {ch_data['index'] + 1}"),
                file_name=f"chapter_{ch_data['index']:03d}.xhtml",
            )
            ch.set_content(f"<h1>{ch_data.get('title', '')}</h1><p>{ch_data['content'].replace(chr(10), '</p><p>')}</p>")
            book.add_item(ch)
            chapter_items.append(ch)

        book.toc = tuple(chapter_items)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav"] + chapter_items  # type: ignore[list-item]

        buf = io.BytesIO()
        epub.write_epub(buf, book, {})
        return buf.getvalue()

    def _make_pdf(self, title: str, manuscript: str) -> bytes:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter)
        styles = getSampleStyleSheet()
        story = [Paragraph(title, styles["Title"]), Spacer(1, 24)]
        for line in manuscript.split("\n"):
            if line.startswith("# "):
                story.append(Paragraph(line[2:], styles["Heading1"]))
            elif line.strip():
                story.append(Paragraph(line, styles["BodyText"]))
        doc.build(story)
        return buf.getvalue()

    def _make_bundle(
        self,
        epub_bytes: bytes,
        pdf_bytes: bytes,
        cover_bytes: bytes,
        cover_brief: str,
        description: str,
        metadata_dict: dict,
    ) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manuscript.epub", epub_bytes)
            zf.writestr("manuscript.pdf", pdf_bytes)
            zf.writestr("cover.jpg", cover_bytes)
            zf.writestr("cover-brief.txt", cover_brief)
            zf.writestr("description.txt", description)
            zf.writestr("metadata.json", json.dumps(metadata_dict, indent=2))
        return buf.getvalue()
```

### `tests/unit/test_assembly.py` (create this file exactly)
```python
"""Unit tests for assembly engines."""
import json
import zipfile
from io import BytesIO
from unittest.mock import MagicMock

import pytest

from worker.memory.store import FictionMemory
from worker.pipeline.assembly import (
    CoverEngine,
    FinalAssemblyEngine,
    FormattingEngine,
    PackagingEngine,
)
from worker.pipeline.base import JobConfig


def make_config() -> JobConfig:
    return JobConfig(
        job_id="asm-job-1",
        title="The Iron Path",
        topic="Warrior redemption",
        mode="fiction",
        audience="Adults",
        tone="Epic",
        target_chapters=3,
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        llm_api_key="k",
        image_provider="dall-e-3",
        image_api_key="k",
    )


LOCKED_CHAPTERS = [
    {"index": 0, "title": "The Beginning", "content": "Once upon a time..."},
    {"index": 1, "title": "The Middle", "content": "Then things got harder..."},
    {"index": 2, "title": "The End", "content": "Finally, peace arrived."},
]


def stub_llm(response: str) -> MagicMock:
    m = MagicMock()
    m.complete.return_value = response
    return m


def test_final_assembly_concatenates_chapters():
    config = make_config()
    engine = FinalAssemblyEngine(llm=stub_llm(""), memory=FictionMemory(config.job_id), config=config)
    ctx = engine.run({"locked_chapters": LOCKED_CHAPTERS})
    assert "Once upon a time" in ctx["manuscript_text"]
    assert "Then things got harder" in ctx["manuscript_text"]
    assert "Finally, peace arrived" in ctx["manuscript_text"]


def test_packaging_engine_returns_metadata():
    config = make_config()
    meta_json = json.dumps({
        "title": "The Iron Path",
        "subtitle": "A Journey of Steel",
        "description": "An epic tale.",
        "keywords": ["epic", "warrior", "redemption", "fantasy", "journey", "steel", "honor"],
        "categories": ["Fantasy", "Action & Adventure"],
    })
    engine = PackagingEngine(llm=stub_llm(meta_json), memory=FictionMemory(config.job_id), config=config)
    ctx = engine.run({"manuscript_text": "content"})
    assert ctx["metadata"]["title"] == "The Iron Path"
    assert len(ctx["metadata"]["keywords"]) == 7


def test_cover_engine_stores_brief_and_bytes():
    config = make_config()
    mock_image_client = MagicMock()
    mock_image_client.generate.return_value = b"fake image bytes"
    engine = CoverEngine(
        llm=stub_llm("A dark, epic cover with gold accents."),
        memory=FictionMemory(config.job_id),
        config=config,
        image_client=mock_image_client,
    )
    ctx = engine.run({"metadata": {"title": "The Iron Path", "subtitle": "", "description": "Epic."}})
    assert ctx["cover_brief"] == "A dark, epic cover with gold accents."
    assert ctx["cover_bytes"] == b"fake image bytes"


def test_formatting_engine_produces_epub_pdf_bundle():
    config = make_config()
    engine = FormattingEngine(llm=stub_llm(""), memory=FictionMemory(config.job_id), config=config)
    ctx = engine.run({
        "manuscript_text": "# Chapter 1: Begin\n\nOnce upon a time.",
        "locked_chapters": LOCKED_CHAPTERS,
        "metadata": {"title": "The Iron Path", "subtitle": "", "description": "", "keywords": [], "categories": []},
        "cover_bytes": b"fake cover",
        "cover_brief": "Brief text",
        "description_text": "An epic tale.",
    })
    assert len(ctx["epub_bytes"]) > 0
    assert len(ctx["pdf_bytes"]) > 0
    # Verify bundle is a valid zip containing all 6 files
    with zipfile.ZipFile(BytesIO(ctx["bundle_bytes"])) as zf:
        names = set(zf.namelist())
    assert "manuscript.epub" in names
    assert "manuscript.pdf" in names
    assert "cover.jpg" in names
    assert "cover-brief.txt" in names
    assert "description.txt" in names
    assert "metadata.json" in names
```

---

## Codebase Context

### Key Patterns in Use
- **CoverEngine takes `image_client` as constructor kwarg:** It is injected by the runner (not built inside the engine), because ImageClient needs job-specific API keys.
- **CoverEngine approval gate:** CoverEngine has a two-phase run. Phase 1 generates the brief and returns `status="awaiting_cover_approval"`. The runner persists state and halts. The dashboard shows the brief with Approve / Edit+Approve buttons. On approval the runner sets `cover_brief_approved=True` (and optionally `cover_brief_revised`) in context and re-runs CoverEngine — which skips brief generation and proceeds to image generation.
- **`@image-creation-expert` role:** This agent is invoked by the dashboard operator to review, critique, and optionally rewrite the cover brief before approving. It does not call the image API — CoverEngine does that after approval.
- **FormattingEngine is pure I/O:** No LLM calls. It reads from context and writes bytes.
- **Bundle is a zip:** All 6 KDP artifacts packaged into a single `.zip` file via `zipfile.ZipFile`.
- **EPUB via ebooklib, PDF via ReportLab:** Both produce `bytes` via `BytesIO` — no temp files on disk.

### Architecture Decisions Affecting This Task
- Requirement 7.4: "The system SHALL run Formatting Engine producing `manuscript.epub` (via ebooklib) and `manuscript.pdf` (via ReportLab)."
- `upload_bytes()` in `storage_service.py` is called by the runner (task-011) after each engine, not by the engines themselves. Engines only produce bytes in context.

---

## Handoff from Previous Task

**Files changed by previous task:** `worker/pipeline/generation.py`, `tests/unit/test_generation.py`.
**Decisions made:** `chapter_passed()` helper for runner. QA/Style threshold = 6/10.
**Context for this task:** Generation layer complete. Now build the assembly layer.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Create `worker/services/__init__.py` — empty file.
2. Create `worker/services/storage_service.py` — paste template exactly.
3. Create `worker/pipeline/assembly.py` — paste template exactly.
4. Create `tests/unit/test_assembly.py` — paste template exactly.
5. Run: `pytest tests/unit/test_assembly.py -v` — verify all 4 tests pass.
6. Run: `ruff check worker/pipeline/assembly.py worker/services/storage_service.py` — verify zero lint errors.

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| PackagingEngine receives non-JSON from LLM | Wrap as `{"title": config.title, "subtitle": "", "description": raw, "keywords": [], "categories": []}` |
| FormattingEngine: `cover_bytes` absent from context | Use `b""` as default (empty cover.jpg in bundle) |
| `_make_epub`: chapter content contains newlines | Replace `\n` with `</p><p>` in HTML |

---

## Acceptance Criteria

- [ ] WHEN FinalAssemblyEngine runs with 3 locked chapters THEN all chapter contents appear in `manuscript_text`
- [ ] WHEN PackagingEngine runs THEN `context["metadata"]` has `title`, `keywords` (7 items), `categories` (2 items)
- [ ] WHEN CoverEngine runs WITHOUT `cover_brief_approved` THEN `context["status"] == "awaiting_cover_approval"` and no image is generated
- [ ] WHEN CoverEngine runs WITH `cover_brief_approved=True` THEN `context["cover_bytes"]` is set and `cover_brief` reflects the approved brief
- [ ] WHEN CoverEngine runs WITH `cover_brief_revised` THEN the revised brief is used as the image prompt (not the original)
- [ ] WHEN FormattingEngine runs THEN bundle zip contains all 6 required files
- [ ] WHEN `pytest tests/unit/test_assembly.py` runs THEN all tests pass

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_
