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
    "- Use specific, concrete language. No vague adjectives "
    "('amazing', 'powerful', 'incredible').\n"
    "- No AI-isms: 'leverage', 'robust', 'seamless', 'cutting-edge', "
    "'delve into', 'tapestry', 'embark'.\n"
    "- No filler openers: 'In today's world', 'Are you ready to', "
    "'This book will change your life'.\n"
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
            parts.append(
                f"# Chapter {ch['index'] + 1}: {ch.get('title', '')}\n\n{ch['content']}\n"
            )
        manuscript = "\n\n".join(parts)
        context["manuscript_text"] = manuscript
        logger.info(
            "[FinalAssembly] Assembled %d chapters for job %s",
            len(chapters),
            self.config.job_id,
        )
        return context


class PackagingEngine(BaseEngine):
    """Generates book description and KDP metadata via LLM."""

    name = "packaging_engine"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        manuscript_excerpt = context.get("manuscript_text", "")[:3000]
        prompt = (
            f"Book title: '{self.config.title}'. Mode: {self.config.mode}. "
            f"Audience: {self.config.audience}.\n"
            f"Manuscript excerpt:\n{manuscript_excerpt}\n\n"
            "Generate KDP metadata as JSON. The 'description' field must be compelling "
            "marketing copy written for Amazon KDP — specific, benefit-driven, no AI-isms, "
            "no filler openers. "
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
        if not context.get("cover_brief_approved", False):
            context["status"] = "awaiting_cover_approval"
            logger.info(
                "[CoverEngine] Awaiting cover brief approval for job %s",
                self.config.job_id,
            )
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
        logger.info(
            "[CoverEngine] Cover generated for job %s (%d bytes)",
            self.config.job_id,
            len(cover_bytes),
        )
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
        logger.info(
            "[FormattingEngine] Bundle created (%d bytes) for job %s",
            len(bundle_bytes),
            self.config.job_id,
        )
        return context

    def _make_epub(
        self, title: str, manuscript: str, chapters_list: list, metadata: dict
    ) -> bytes:
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
            content = ch_data["content"].replace(chr(10), "</p><p>")
            ch.set_content(
                f"<h1>{ch_data.get('title', '')}</h1><p>{content}</p>"
            )
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
