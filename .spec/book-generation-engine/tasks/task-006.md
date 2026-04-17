---
task: 006
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: ai-ml-expert
depends_on: [002, 005]
---

# Task 006: Shared Core Engines (Entry Gate → Blueprint Selector)

## Skills
- .kit/skills/data-science-ml/ai-engineer/SKILL.md
- .kit/skills/languages/python-patterns/SKILL.md
- .kit/skills/research-docs/copywriting/SKILL.md

## Agents
- @ai-ml-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else.

---

## Objective

Implement `worker/pipeline/shared_core.py` containing 5 engine classes — Entry Gate, Intent Engine, Audience Engine, Positioning Engine, and Content Blueprint Selector — all extending `BaseEngine`, executed in sequence to validate input and branch the pipeline.

---

## Files

### Create
| File | Purpose |
|------|---------|
| `worker/pipeline/base.py` | BaseEngine abstract class + JobConfig Pydantic model |
| `worker/pipeline/shared_core.py` | 5 shared core engines |
| `tests/unit/test_shared_core.py` | Unit tests with stub LLM responses |

---

## Dependencies

```bash
# No new packages.
```

---

## Code Templates

### `worker/pipeline/base.py` (create this file exactly)
```python
"""Base classes for all pipeline engines."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field

from worker.clients.llm_client import LLMClient
from worker.memory.store import MemoryStore


class JobConfig(BaseModel):
    """Validated configuration for a book generation job."""
    job_id: str
    title: str = Field(min_length=1, max_length=500)
    topic: str = Field(min_length=1, max_length=2000)
    mode: Literal["fiction", "non_fiction"]
    audience: str = Field(min_length=1, max_length=500)
    tone: str = Field(min_length=1, max_length=200)
    target_chapters: int = Field(ge=3, le=50, default=12)
    llm_provider: str
    llm_model: str
    llm_api_key: str
    llm_base_url: str | None = None
    image_provider: str
    image_api_key: str
    notification_email: str | None = None


class BaseEngine(ABC):
    """All pipeline engines extend this class."""
    name: str = "base"

    def __init__(self, llm: LLMClient, memory: MemoryStore, config: JobConfig) -> None:
        self.llm = llm
        self.memory = memory
        self.config = config

    @abstractmethod
    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the engine. Receives context dict, returns updated context dict."""
        ...
```

### `worker/pipeline/shared_core.py` (create this file exactly)
```python
"""Shared core pipeline engines. Run for both fiction and non-fiction."""
from __future__ import annotations

import json
import logging
from typing import Any

from worker.pipeline.base import BaseEngine

logger = logging.getLogger(__name__)


class EntryGateEngine(BaseEngine):
    name = "entry_gate"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Validate job config and produce validated_input dict."""
        logger.info("[EntryGate] Validating job %s", self.config.job_id)
        validated = {
            "job_id": self.config.job_id,
            "title": self.config.title.strip(),
            "topic": self.config.topic.strip(),
            "mode": self.config.mode,
            "audience": self.config.audience.strip(),
            "tone": self.config.tone.strip(),
            "target_chapters": self.config.target_chapters,
        }
        context["validated_input"] = validated
        context["status"] = "planning"
        logger.info("[EntryGate] Validated input for job %s", self.config.job_id)
        return context


class IntentEngine(BaseEngine):
    name = "intent_engine"

    SYSTEM = "You are a book strategy expert. Output JSON only."
    PROMPT_TEMPLATE = (
        "Book: '{title}'. Topic: '{topic}'. Mode: {mode}. Audience: {audience}.\n"
        "Define the book's intent as JSON: "
        '{{ "transformation": "...", "outcome": "...", "reader_state_before": "...", "reader_state_after": "..." }}'
    )

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        logger.info("[IntentEngine] Running for job %s", self.config.job_id)
        prompt = self.PROMPT_TEMPLATE.format(
            title=self.config.title,
            topic=self.config.topic,
            mode=self.config.mode,
            audience=self.config.audience,
        )
        raw = self.llm.complete(prompt, self.SYSTEM)
        try:
            intent = json.loads(raw)
        except json.JSONDecodeError:
            intent = {"transformation": raw, "outcome": "", "reader_state_before": "", "reader_state_after": ""}
        context["intent"] = intent
        self.memory.update("intent", intent)
        return context


class AudienceEngine(BaseEngine):
    name = "audience_engine"

    SYSTEM = "You are an audience analyst. Output JSON only."
    PROMPT_TEMPLATE = (
        "Book: '{title}'. Audience: '{audience}'. Tone: '{tone}'.\n"
        "Define the audience profile as JSON: "
        '{{ "demographics": "...", "expectations": "...", "depth_tolerance": "beginner|intermediate|advanced", "reading_context": "..." }}'
    )

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        logger.info("[AudienceEngine] Running for job %s", self.config.job_id)
        prompt = self.PROMPT_TEMPLATE.format(
            title=self.config.title,
            audience=self.config.audience,
            tone=self.config.tone,
        )
        raw = self.llm.complete(prompt, self.SYSTEM)
        try:
            audience_profile = json.loads(raw)
        except json.JSONDecodeError:
            audience_profile = {"demographics": raw, "expectations": "", "depth_tolerance": "intermediate", "reading_context": ""}
        context["audience_profile"] = audience_profile
        self.memory.update("audience_profile", audience_profile)
        return context


class PositioningEngine(BaseEngine):
    name = "positioning_engine"

    SYSTEM = "You are a book positioning strategist. Output JSON only."
    PROMPT_TEMPLATE = (
        "Book: '{title}'. Topic: '{topic}'. Audience: '{audience}'.\n"
        "Define positioning as JSON: "
        '{{ "unique_angle": "...", "market_differentiation": "...", "what_book_avoids": "..." }}'
    )

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        logger.info("[PositioningEngine] Running for job %s", self.config.job_id)
        prompt = self.PROMPT_TEMPLATE.format(
            title=self.config.title,
            topic=self.config.topic,
            audience=self.config.audience,
        )
        raw = self.llm.complete(prompt, self.SYSTEM)
        try:
            positioning = json.loads(raw)
        except json.JSONDecodeError:
            positioning = {"unique_angle": raw, "market_differentiation": "", "what_book_avoids": ""}
        context["positioning"] = positioning
        self.memory.update("positioning", positioning)
        return context


class ContentBlueprintSelectorEngine(BaseEngine):
    name = "content_blueprint_selector"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        logger.info("[BlueprintSelector] Mode=%s for job %s", self.config.mode, self.config.job_id)
        context["branch"] = self.config.mode  # "fiction" or "non_fiction"
        return context
```

### `tests/unit/test_shared_core.py` (create this file exactly)
```python
"""Unit tests for shared core engines."""
import json
from unittest.mock import MagicMock

import pytest

from worker.memory.store import FictionMemory, NonFictionMemory
from worker.pipeline.base import JobConfig
from worker.pipeline.shared_core import (
    AudienceEngine,
    ContentBlueprintSelectorEngine,
    EntryGateEngine,
    IntentEngine,
    PositioningEngine,
)


def make_config(mode: str = "fiction") -> JobConfig:
    return JobConfig(
        job_id="test-job-1",
        title="The Iron Path",
        topic="Stoicism applied to modern leadership",
        mode=mode,
        audience="Professionals aged 30-50",
        tone="Authoritative yet accessible",
        target_chapters=10,
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        llm_api_key="test-key",
        image_provider="dall-e-3",
        image_api_key="img-key",
    )


def make_stub_llm(response: str) -> MagicMock:
    llm = MagicMock()
    llm.complete.return_value = response
    return llm


def test_entry_gate_sets_validated_input_and_status():
    config = make_config("fiction")
    mem = FictionMemory(config.job_id)
    engine = EntryGateEngine(llm=make_stub_llm(""), memory=mem, config=config)
    ctx = engine.run({})
    assert ctx["validated_input"]["job_id"] == "test-job-1"
    assert ctx["validated_input"]["mode"] == "fiction"
    assert ctx["status"] == "planning"


def test_intent_engine_parses_json_from_llm():
    config = make_config()
    mem = FictionMemory(config.job_id)
    intent_json = json.dumps({
        "transformation": "From reactive to proactive",
        "outcome": "Confident leadership",
        "reader_state_before": "Stressed",
        "reader_state_after": "Empowered",
    })
    engine = IntentEngine(llm=make_stub_llm(intent_json), memory=mem, config=config)
    ctx = engine.run({})
    assert ctx["intent"]["transformation"] == "From reactive to proactive"
    assert mem.get("intent") == ctx["intent"]


def test_intent_engine_handles_non_json_llm_response():
    config = make_config()
    mem = FictionMemory(config.job_id)
    engine = IntentEngine(llm=make_stub_llm("Not JSON at all"), memory=mem, config=config)
    ctx = engine.run({})
    assert "transformation" in ctx["intent"]


def test_audience_engine_stores_profile_in_memory():
    config = make_config()
    mem = FictionMemory(config.job_id)
    profile_json = json.dumps({
        "demographics": "30-50 professionals",
        "expectations": "Practical advice",
        "depth_tolerance": "intermediate",
        "reading_context": "commute",
    })
    engine = AudienceEngine(llm=make_stub_llm(profile_json), memory=mem, config=config)
    ctx = engine.run({})
    assert mem.get("audience_profile")["depth_tolerance"] == "intermediate"


def test_blueprint_selector_fiction():
    config = make_config("fiction")
    mem = FictionMemory(config.job_id)
    engine = ContentBlueprintSelectorEngine(llm=make_stub_llm(""), memory=mem, config=config)
    ctx = engine.run({})
    assert ctx["branch"] == "fiction"


def test_blueprint_selector_non_fiction():
    config = make_config("non_fiction")
    mem = NonFictionMemory(config.job_id)
    engine = ContentBlueprintSelectorEngine(llm=make_stub_llm(""), memory=mem, config=config)
    ctx = engine.run({})
    assert ctx["branch"] == "non_fiction"
```

---

## Codebase Context

### Key Patterns in Use
- **Engines are stateless between runs:** All state goes into `self.memory` or `context` dict. Never use instance variables to store generation results.
- **JSON parse with fallback:** Every engine that calls `json.loads()` wraps it in a try/except and falls back to a safe dict.
- **`context` dict is the pipeline bus:** Each engine receives and returns the same dict, adding its outputs.
- **`self.memory.update()` mirrors context:** Both context and memory get updated so the runner can persist memory at any point.

### Architecture Decisions Affecting This Task
- `BaseEngine.run(context)` is the contract. All 5 engines implement it.
- Entry Gate is the only engine that validates input — downstream engines trust `context["validated_input"]`.
- Blueprint Selector sets `context["branch"]` to `"fiction"` or `"non_fiction"` — the runner uses this to choose the next path.

---

## Handoff from Previous Task

**Files changed by previous task:** `worker/memory/store.py`, `tests/unit/test_memory_store.py`.
**Decisions made:** MemoryStore snapshot is deep copy. FictionMemory and NonFictionMemory schemas established.
**Context for this task:** Memory system is done. Now build the first pipeline stage using LLMClient + MemoryStore.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Create `worker/pipeline/base.py` — paste template exactly.
2. Create `worker/pipeline/shared_core.py` — paste template exactly.
3. Create `tests/unit/test_shared_core.py` — paste template exactly.
4. Run: `pytest tests/unit/test_shared_core.py -v` — verify all 6 tests pass.
5. Run: `ruff check worker/pipeline/` — verify zero lint errors.
6. Run: `mypy worker/pipeline/base.py worker/pipeline/shared_core.py` — verify zero type errors.

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| LLM returns invalid JSON in IntentEngine | Wrap raw response in `{"transformation": raw, "outcome": "", ...}` |
| LLM returns invalid JSON in AudienceEngine | Wrap in `{"demographics": raw, "expectations": "", "depth_tolerance": "intermediate", "reading_context": ""}` |
| LLM returns invalid JSON in PositioningEngine | Wrap in `{"unique_angle": raw, "market_differentiation": "", "what_book_avoids": ""}` |
| Blueprint Selector reads mode | Use `self.config.mode` directly — never call LLM |

---

## Acceptance Criteria

- [ ] WHEN EntryGate runs THEN `context["validated_input"]` and `context["status"] == "planning"` are set
- [ ] WHEN IntentEngine receives non-JSON LLM response THEN a fallback dict is stored (no exception raised)
- [ ] WHEN BlueprintSelector runs in fiction mode THEN `context["branch"] == "fiction"`
- [ ] WHEN `pytest tests/unit/test_shared_core.py` runs THEN all 6 tests pass

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_
