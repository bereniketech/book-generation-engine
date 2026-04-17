"""Unit tests for MemoryStore, FictionMemory, NonFictionMemory."""
import pytest

from worker.memory.store import FictionMemory, MemoryStore, NonFictionMemory


def test_base_store_update_and_get():
    store = MemoryStore(job_id="job-1", mode="fiction")
    store.update("key1", "value1")
    assert store.get("key1") == "value1"


def test_base_store_get_default():
    store = MemoryStore(job_id="job-1", mode="fiction")
    assert store.get("missing", default="fallback") == "fallback"


def test_base_store_snapshot_is_copy():
    store = MemoryStore(job_id="job-1", mode="fiction")
    store.update("x", [1, 2, 3])
    snap = store.snapshot()
    snap["data"]["x"].append(99)
    assert store.get("x") == [1, 2, 3]


def test_base_store_snapshot_contains_job_id_and_mode():
    store = MemoryStore(job_id="job-42", mode="non_fiction")
    snap = store.snapshot()
    assert snap["job_id"] == "job-42"
    assert snap["mode"] == "non_fiction"


def test_fiction_memory_add_character():
    mem = FictionMemory(job_id="j1")
    mem.add_character("Alice", role="protagonist", description="Brave woman", arc="Hero journey")
    chars = mem.get("characters")
    assert "Alice" in chars
    assert chars["Alice"]["role"] == "protagonist"


def test_fiction_memory_add_world_rule_no_duplicates():
    mem = FictionMemory(job_id="j1")
    mem.add_world_rule("Magic costs energy")
    mem.add_world_rule("Magic costs energy")
    assert mem.get("world_rules").count("Magic costs energy") == 1


def test_fiction_memory_lock_chapter():
    mem = FictionMemory(job_id="j1")
    mem.lock_chapter(0)
    mem.lock_chapter(0)
    assert mem.get("locked_chapters") == [0]


def test_fiction_memory_timeline_ordering():
    mem = FictionMemory(job_id="j1")
    mem.add_timeline_event(0, "Hero meets mentor")
    mem.add_timeline_event(1, "Hero faces first trial")
    timeline = mem.get("timeline")
    assert len(timeline) == 2
    assert timeline[0]["chapter_index"] == 0


def test_non_fiction_memory_add_concept_no_duplicates():
    mem = NonFictionMemory(job_id="j2")
    mem.add_concept("Growth mindset")
    mem.add_concept("Growth mindset")
    assert mem.get("concepts_introduced").count("Growth mindset") == 1


def test_non_fiction_memory_is_concept_used():
    mem = NonFictionMemory(job_id="j2")
    mem.add_concept("Stoicism")
    assert mem.is_concept_used("Stoicism") is True
    assert mem.is_concept_used("Epicureanism") is False


def test_non_fiction_memory_add_evidence():
    mem = NonFictionMemory(job_id="j2")
    mem.add_evidence("Harvard Study 2020", "Daily habits improve focus by 40%")
    evidence = mem.get("evidence_used")
    assert len(evidence) == 1
    assert evidence[0]["source"] == "Harvard Study 2020"


def test_non_fiction_memory_snapshot_includes_research_summary():
    mem = NonFictionMemory(job_id="j2")
    mem.update("research_summary", "Detailed research on leadership.")
    snap = mem.snapshot()
    assert snap["data"]["research_summary"] == "Detailed research on leadership."
