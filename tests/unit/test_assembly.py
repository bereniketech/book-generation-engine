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
    ctx = engine.run({"metadata": {"title": "The Iron Path", "subtitle": "", "description": "Epic."}, "cover_brief_approved": True})
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
