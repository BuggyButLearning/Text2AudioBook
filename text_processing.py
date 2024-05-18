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

def split_text(text, max_length=3500):
    import re
    chunks = []
    positions = []
    sentences = []
    start = 0
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            positions.append(start)
            sentences.append(text.split('.')[0])  # Simple split for the starting sentence
            break
        split_at = max_length
        if len(text) > max_length:
            match = re.search(r'[.!?]', text[:max_length][::-1])
            if match:
                split_at = max_length - match.start()
        if split_at == 0:  # no punctuation found within max_length, force split
            split_at = max_length
        chunks.append(text[:split_at].strip())
        positions.append(start)
        sentences.append(text[:split_at].split('.')[0])  # Simple split for the starting sentence
        start += split_at
        text = text[split_at:].strip()
    return chunks, positions, sentences
