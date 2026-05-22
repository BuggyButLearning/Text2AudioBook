import logging
import re


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


def split_text(text, max_length=3500):
    chunks = []
    positions = []
    sentences = []
    text = _normalize_text(text)
    if not text:
        return chunks, positions, sentences

    raw_paragraphs = [paragraph.strip() for paragraph in re.split(r'\n\s*\n', text) if paragraph.strip()]
    cursor = 0
    current_chunk = ""
    current_position = 0

    def flush_chunk():
        nonlocal current_chunk, current_position
        cleaned = current_chunk.strip()
        if cleaned:
            chunks.append(cleaned)
            positions.append(current_position)
            sentences.append(_chunk_preview(cleaned))
        current_chunk = ""

    for paragraph in raw_paragraphs:
        paragraph_start = text.find(paragraph, cursor)
        if paragraph_start == -1:
            paragraph_start = cursor
        cursor = paragraph_start + len(paragraph)
        paragraph_block = paragraph + "\n\n"

        if len(paragraph_block.strip()) > max_length:
            for sentence in _sentence_split(paragraph):
                sentence_start = text.find(sentence, current_position if current_chunk else paragraph_start)
                if sentence_start == -1:
                    sentence_start = paragraph_start
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
                        piece_pos = text.find(piece, sentence_start + hard_start)
                        chunks.append(piece)
                        positions.append(piece_pos if piece_pos != -1 else sentence_start + hard_start)
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
