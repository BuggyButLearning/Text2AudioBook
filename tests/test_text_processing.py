from text_processing import (
    _chunk_preview,
    _normalize_text,
    _sentence_split,
    read_text_from_file,
    split_text,
)


class TestReadTextFromFile:
    def test_reads_utf8_content(self, tmp_path):
        p = tmp_path / "sample.txt"
        p.write_text("hello world", encoding="utf-8")
        assert read_text_from_file(str(p)) == "hello world"

    def test_returns_none_on_missing_file(self, tmp_path):
        # CHARACTERIZED — current behavior returns None on error rather than raising.
        result = read_text_from_file(str(tmp_path / "nope.txt"))
        assert result is None


class TestNormalizeText:
    def test_replaces_crlf(self):
        assert _normalize_text("a\r\nb") == "a\nb"

    def test_replaces_cr(self):
        assert _normalize_text("a\rb") == "a\nb"

    def test_strips_outer_whitespace(self):
        assert _normalize_text("  hello  ") == "hello"

    def test_empty_input_returns_empty(self):
        assert _normalize_text("") == ""

    def test_none_input_returns_empty(self):
        assert _normalize_text(None) == ""


class TestSentenceSplit:
    def test_splits_on_period(self):
        assert _sentence_split("One. Two. Three.") == ["One.", "Two.", "Three."]

    def test_splits_on_question_and_bang(self):
        assert _sentence_split("Hi? Yes! Sure.") == ["Hi?", "Yes!", "Sure."]

    def test_drops_empties(self):
        assert _sentence_split("   ") == []


class TestChunkPreview:
    def test_returns_first_sentence_up_to_limit(self):
        text = "This is one. This is two."
        assert _chunk_preview(text) == "This is one."

    def test_truncates_at_max_preview(self):
        text = "a" * 500
        assert len(_chunk_preview(text, max_preview=120)) == 120

    def test_empty_input_returns_empty(self):
        assert _chunk_preview("") == ""


class TestSplitText:
    def test_empty_returns_three_empty_lists(self):
        chunks, positions, sentences = split_text("")
        assert chunks == []
        assert positions == []
        assert sentences == []

    def test_short_input_returns_single_chunk(self):
        text = "Hello world. This is short."
        chunks, positions, sentences = split_text(text, max_length=3500)
        assert len(chunks) == 1
        assert chunks[0] == text
        assert positions == [0]
        assert sentences[0].startswith("Hello world")

    def test_paragraph_boundary_preferred(self):
        text = "First para sentence.\n\nSecond para sentence."
        chunks, _, _ = split_text(text, max_length=3500)
        assert len(chunks) == 1

    def test_splits_when_paragraph_exceeds_max(self):
        long_para = " ".join([f"Sentence {i}." for i in range(200)])
        chunks, positions, sentences = split_text(long_para, max_length=100)
        assert len(chunks) > 1
        assert all(len(c) <= 100 for c in chunks)
        assert len(sentences) == len(chunks)

    def test_hard_split_when_single_sentence_exceeds_max(self):
        sentence = "a" * 500
        chunks, _, _ = split_text(sentence, max_length=100)
        assert len(chunks) >= 5
        assert all(len(c) <= 100 for c in chunks)

    def test_chunks_and_positions_have_same_length(self):
        text = "Sentence one. Sentence two.\n\nNew para here. Another one."
        chunks, positions, sentences = split_text(text, max_length=20)
        assert len(chunks) == len(positions) == len(sentences)

    def test_preserves_relative_order(self):
        text = "Alpha sentence.\n\nBeta sentence.\n\nGamma sentence."
        chunks, _, _ = split_text(text, max_length=20)
        joined = " ".join(chunks)
        assert joined.index("Alpha") < joined.index("Beta") < joined.index("Gamma")
