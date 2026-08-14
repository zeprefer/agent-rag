from dataclasses import dataclass
import re

from app.core.config import settings
from app.services.document_parsers import ParsedSection


@dataclass(frozen=True)
class TextChunk:
    content: str
    heading_path: str | None
    page_number: int | None
    token_count: int
    metadata: dict


def build_chunks(sections: list[ParsedSection]) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    target_chars = max(settings.chunk_target_tokens * 2, 600)
    overlap_chars = max(settings.chunk_overlap_tokens * 2, 0)

    for section in sections:
        paragraphs = _split_paragraphs(section.text)
        buffer = ""
        section_index = 0

        for paragraph in paragraphs:
            candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
            if len(candidate) <= target_chars:
                buffer = candidate
                continue

            if buffer:
                chunks.append(_make_chunk(section=section, content=buffer, section_index=section_index))
                section_index += 1
                buffer = _tail(buffer, overlap_chars)

            if len(paragraph) > target_chars:
                for piece in _split_long_text(paragraph, target_chars, overlap_chars):
                    chunks.append(_make_chunk(section=section, content=piece, section_index=section_index))
                    section_index += 1
                buffer = ""
            else:
                buffer = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph

        if buffer:
            chunks.append(_make_chunk(section=section, content=buffer, section_index=section_index))

    return chunks


def estimate_token_count(text: str) -> int:
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_words = len(re.findall(r"[A-Za-z0-9_]+", text))
    punctuation = max(len(text) - cjk_chars - sum(len(word) for word in re.findall(r"[A-Za-z0-9_]+", text)), 0)
    return max(cjk_chars + latin_words + punctuation // 4, 1)


def _make_chunk(*, section: ParsedSection, content: str, section_index: int) -> TextChunk:
    normalized = content.strip()
    return TextChunk(
        content=normalized,
        heading_path=section.heading_path,
        page_number=section.page_number,
        token_count=estimate_token_count(normalized),
        metadata={"section_index": section_index},
    )


def _split_paragraphs(text: str) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", text) if paragraph.strip()]
    if paragraphs:
        return paragraphs
    return [text.strip()] if text.strip() else []


def _split_long_text(text: str, target_chars: int, overlap_chars: int) -> list[str]:
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + target_chars, len(text))
        pieces.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(end - overlap_chars, start + 1)
    return [piece for piece in pieces if piece]


def _tail(text: str, length: int) -> str:
    if length <= 0:
        return ""
    return text[-length:].strip()

