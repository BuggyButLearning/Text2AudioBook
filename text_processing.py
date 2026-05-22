import logging
import re


# OpenAI TTS hard input ceiling per OpenAI docs. Splitting must never produce a chunk
# larger than this. Phase 6.2 / 6.3 may add per-provider constants alongside.
OPENAI_TTS_MAX_INPUT_CHARS = 4096

# Safe default chunk size: leaves headroom for whitespace-normalization rounding
# and avoids brushing the API limit. Callers can override via max_length=...
DEFAULT_CHUNK_MAX = 3500


def read_text_from_file(file_path):
    """Reads and returns the content of a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        logging.info("Successfully read text from input file.")
        return content
    except Exception as e:
        logging.error(f"Error reading the input file: {e}")
        return None


def _normalize_text(text):
    return re.sub(r"\r\n?", "\n", text or "").strip()


def _sentence_split(paragraph):
    sentences = re.split(r'(?<=[.!?])\s+', paragraph.strip())
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def _chunk_preview(text, max_preview=120):
    preview = re.split(r'(?<=[.!?])\s+', text.strip())[0].strip() if text.strip() else ""
    return preview[:max_preview]


def split_text(text, max_length=DEFAULT_CHUNK_MAX):
    chunks = []
    positions = []
    sentences = []
    text = _normalize_text(text)
    if not text:
        return chunks, positions, sentences

    raw_paragraphs = [paragraph.strip() for paragraph in re.split(r'\n\s*\n', text) if paragraph.strip()]

    # Forward-only cursor: every subsequent find searches strictly AT-OR-AFTER this.
    # Each successful match advances the cursor past the matched substring so duplicates
    # in the source resolve to distinct, source-ordered offsets.
    find_cursor = 0
    current_chunk = ""
    current_position = 0

    def _locate(substring, fallback):
        nonlocal find_cursor
        idx = text.find(substring, find_cursor) if substring else -1
        if idx == -1:
            # Audit-added S2: defensive observability. paragraphs/sentences are
            # extracted from the normalized text via re.split, so find() SHOULD
            # always succeed. If it doesn't, normalization has desynced from search
            # -- surface it under DEBUG so maintainers see it in CI runs that opt in.
            logging.debug(
                "text_processing._locate: substring not found at-or-after cursor=%d; "
                "using fallback. substring_preview=%r",
                find_cursor, substring[:30],
            )
            return fallback
        find_cursor = idx + len(substring)
        return idx

    def flush_chunk():
        nonlocal current_chunk, current_position
        cleaned = current_chunk.strip()
        if cleaned:
            chunks.append(cleaned)
            positions.append(current_position)
            sentences.append(_chunk_preview(cleaned))
        current_chunk = ""

    for paragraph in raw_paragraphs:
        paragraph_start = _locate(paragraph, find_cursor)

        if len(paragraph) > max_length:
            for sentence in _sentence_split(paragraph):
                sentence_start = _locate(sentence, paragraph_start)
                candidate = f"{current_chunk} {sentence}".strip() if current_chunk else sentence
                if not current_chunk:
                    current_position = sentence_start

                if len(candidate) <= max_length:
                    current_chunk = candidate
                    continue

                flush_chunk()

                if len(sentence) <= max_length:
                    current_chunk = sentence
                    current_position = sentence_start
                    continue

                hard_start = 0
                while hard_start < len(sentence):
                    hard_end = min(hard_start + max_length, len(sentence))
                    piece = sentence[hard_start:hard_end].strip()
                    if piece:
                        # Hard-split pieces compute position arithmetically; no need to
                        # find() since we know the slice location exactly.
                        piece_pos = sentence_start + hard_start
                        chunks.append(piece)
                        positions.append(piece_pos)
                        sentences.append(_chunk_preview(piece))
                    hard_start = hard_end
            continue

        candidate = f"{current_chunk}\n\n{paragraph}".strip() if current_chunk else paragraph.strip()
        if not current_chunk:
            current_position = paragraph_start

        if len(candidate) <= max_length:
            current_chunk = candidate
        else:
            flush_chunk()
            current_chunk = paragraph.strip()
            current_position = paragraph_start

    flush_chunk()
    return chunks, positions, sentences
