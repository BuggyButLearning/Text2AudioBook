from text_processing import (
    DEFAULT_CHUNK_MAX,
    OPENAI_TTS_MAX_INPUT_CHARS,
    SUPPORTED_INPUT_EXTENSIONS,
    _chunk_preview,
    _normalize_text,
    _sentence_split,
    read_text_from_file,
    split_text,
    strip_markdown,
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

    def test_reads_md_file_and_strips_markdown(self, tmp_path):
        p = tmp_path / "sample.md"
        p.write_text("# Title\n\n**Bold** and *italic*.", encoding="utf-8")
        out = read_text_from_file(str(p))
        assert "Title" in out
        assert "#" not in out
        assert "**" not in out
        assert "Bold" in out
        assert "italic" in out

    def test_reads_markdown_extension_strips(self, tmp_path):
        p = tmp_path / "sample.markdown"
        p.write_text("# Header", encoding="utf-8")
        assert read_text_from_file(str(p)).strip() == "Header"

    def test_txt_file_left_unchanged(self, tmp_path):
        """.txt path must NOT strip — # is valid text content there."""
        p = tmp_path / "sample.txt"
        p.write_text("# this is not a header", encoding="utf-8")
        assert read_text_from_file(str(p)) == "# this is not a header"


class TestSupportedInputExtensions:
    def test_includes_txt_and_md(self):
        assert ".txt" in SUPPORTED_INPUT_EXTENSIONS
        assert ".md" in SUPPORTED_INPUT_EXTENSIONS
        assert ".markdown" in SUPPORTED_INPUT_EXTENSIONS


class TestStripMarkdown:
    def test_atx_header_unwrapped(self):
        assert strip_markdown("# Hello").strip() == "Hello"
        assert strip_markdown("### Sub").strip() == "Sub"

    def test_setext_header_unwrapped(self):
        out = strip_markdown("Title\n=====")
        assert "Title" in out
        assert "=" not in out

    def test_bold_unwrapped(self):
        assert "Bold" in strip_markdown("**Bold** text")
        assert "**" not in strip_markdown("**Bold** text")

    def test_italic_unwrapped(self):
        assert "italic" in strip_markdown("*italic*")
        assert "*" not in strip_markdown("*italic*")

    def test_strikethrough_unwrapped(self):
        out = strip_markdown("~~gone~~")
        assert "gone" in out
        assert "~" not in out

    def test_inline_code_unwrapped(self):
        out = strip_markdown("Use `foo()` to call")
        assert "foo()" in out
        assert "`" not in out

    def test_fenced_code_removed(self):
        text = "Before\n\n```python\nprint('hi')\n```\n\nAfter"
        out = strip_markdown(text)
        assert "Before" in out
        assert "After" in out
        assert "print" not in out
        assert "```" not in out

    def test_link_keeps_text_drops_url(self):
        out = strip_markdown("See [the docs](https://example.com) here")
        assert "the docs" in out
        assert "https://example.com" not in out
        assert "[" not in out

    def test_image_keeps_alt_drops_url(self):
        out = strip_markdown("![cat photo](cat.jpg)")
        assert "cat photo" in out
        assert "cat.jpg" not in out

    def test_list_markers_removed(self):
        out = strip_markdown("- one\n- two\n- three")
        assert "one" in out
        assert "two" in out
        assert "- " not in out

    def test_numbered_list_markers_removed(self):
        out = strip_markdown("1. one\n2. two")
        assert "one" in out
        assert "1." not in out

    def test_blockquote_stripped(self):
        out = strip_markdown("> quoted line")
        assert "quoted line" in out
        assert ">" not in out

    def test_hr_removed(self):
        out = strip_markdown("Before\n\n---\n\nAfter")
        assert "Before" in out
        assert "After" in out
        assert "---" not in out

    def test_html_tag_removed(self):
        out = strip_markdown("Hello <span>world</span>")
        assert "Hello" in out
        assert "world" in out
        assert "<" not in out

    def test_table_separator_and_pipes(self):
        text = "| a | b |\n|---|---|\n| 1 | 2 |"
        out = strip_markdown(text)
        assert "a" in out and "b" in out
        assert "1" in out and "2" in out
        assert "|" not in out
        assert "---" not in out

    def test_empty_input_returns_empty(self):
        assert strip_markdown("") == ""
        assert strip_markdown(None) is None

    def test_plain_text_unchanged(self):
        out = strip_markdown("Just a sentence with no markdown.")
        assert out == "Just a sentence with no markdown."

    def test_combined_real_world_sample(self):
        sample = (
            "# Chapter 1\n\n"
            "Once upon a *time*, there was a **brave** knight.\n\n"
            "- He had a sword\n"
            "- And a shield\n\n"
            "> 'Onward!' he cried.\n\n"
            "See [the map](map.png) for details.\n\n"
            "```\nignored code block\n```\n"
        )
        out = strip_markdown(sample)
        for token in ["#", "**", "```", "[", "]", "(", "> "]:
            assert token not in out, f"residual markdown token {token!r} in output"
        for word in ["Chapter 1", "time", "brave", "knight", "sword", "shield", "Onward", "the map"]:
            assert word in out, f"missing content word {word!r}"
        assert "ignored code block" not in out


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


class TestSplitTextBudget:
    def test_default_chunk_max_under_openai_limit(self):
        assert DEFAULT_CHUNK_MAX < OPENAI_TTS_MAX_INPUT_CHARS, (
            f"DEFAULT_CHUNK_MAX={DEFAULT_CHUNK_MAX} must be < "
            f"OPENAI_TTS_MAX_INPUT_CHARS={OPENAI_TTS_MAX_INPUT_CHARS}"
        )

    def test_openai_limit_value_matches_docs(self):
        assert OPENAI_TTS_MAX_INPUT_CHARS == 4096

    def test_default_max_length_is_default_chunk_max(self):
        import inspect
        sig = inspect.signature(split_text)
        assert sig.parameters["max_length"].default == DEFAULT_CHUNK_MAX

    def test_no_chunk_exceeds_openai_limit_on_long_input(self):
        text = ("This is a sentence. " * 800).strip()
        chunks, _, _ = split_text(text)
        assert all(len(c) <= OPENAI_TTS_MAX_INPUT_CHARS for c in chunks)
        assert all(len(c) <= DEFAULT_CHUNK_MAX for c in chunks)


class TestSplitTextPositions:
    def _reconstruct_check(self, text, chunks, positions):
        """For each chunk, the text starting at positions[i] must begin with the
        chunk's content (whitespace-tolerant first-20-char prefix check).
        Audit S4: assert non-empty chunks and a source-slice length floor so a
        past-EOF position fails fast."""
        for chunk, pos in zip(chunks, positions):
            assert len(chunk) > 0, f"empty chunk at position {pos}"
            prefix = chunk.lstrip()[:40]
            source_slice = text[pos:pos + len(prefix) + 10].lstrip()
            assert len(source_slice) >= min(len(prefix), 10), (
                f"source slice too short at position {pos} "
                f"(text length={len(text)}, slice={source_slice!r})"
            )
            assert source_slice.startswith(prefix[:20]), (
                f"Reconstruction failed: chunk prefix {prefix[:20]!r} "
                f"not found at position {pos} (source slice: {source_slice[:30]!r})"
            )

    def test_positions_are_monotonic_non_decreasing(self):
        text = "Alpha sentence.\n\nBeta sentence.\n\nGamma sentence."
        chunks, positions, _ = split_text(text, max_length=20)
        assert positions == sorted(positions), (
            f"positions not monotonic: {positions}"
        )

    def test_distinct_chunks_have_distinct_positions(self):
        """Audit S3: trap the [0, 0, 0] regression -- a broken implementation that
        always returns 0 would pass the monotonic test."""
        text = "Alpha sentence.\n\nBeta sentence.\n\nGamma sentence."
        chunks, positions, _ = split_text(text, max_length=20)
        assert len(chunks) >= 2, f"expected >= 2 chunks, got {len(chunks)}"
        assert len(set(positions)) >= 2, (
            f"all positions collapsed to the same value: {positions}"
        )

    def test_duplicate_paragraphs_get_distinct_positions(self):
        # Regression for the position-accuracy bug: two identical paragraphs must
        # resolve to two distinct, source-ordered offsets.
        text = "He said.\n\nShe said.\n\nHe said."
        chunks, positions, _ = split_text(text, max_length=10)
        he_positions = [p for c, p in zip(chunks, positions) if "He said" in c]
        assert len(he_positions) == 2, (
            f"expected 2 'He said' chunks, got {len(he_positions)}: chunks={chunks}"
        )
        assert he_positions[0] != he_positions[1], (
            f"duplicate 'He said' chunks collapsed to same position: {he_positions}"
        )
        assert he_positions[0] < he_positions[1]

    def test_reconstruction_short_input(self):
        text = "Hello world. This is short."
        chunks, positions, _ = split_text(text)
        self._reconstruct_check(text, chunks, positions)

    def test_reconstruction_multi_paragraph(self):
        text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here."
        chunks, positions, _ = split_text(text, max_length=20)
        self._reconstruct_check(text, chunks, positions)

    def test_reconstruction_hard_split_sentence(self):
        text = "a" * 500
        chunks, positions, _ = split_text(text, max_length=100)
        for chunk, pos in zip(chunks, positions):
            assert text[pos:pos + len(chunk)] == chunk


class TestSplitTextEdgeCases:
    def test_unicode_content_survives(self):
        text = "Café — François said \"hello\". Ɛach line has Üñïcode."
        chunks, _, _ = split_text(text)
        assert len(chunks) >= 1
        assert "Café" in " ".join(chunks)
        assert "François" in " ".join(chunks)

    def test_multiple_blank_lines_between_paragraphs(self):
        text = "Para one.\n\n\n\n\n\nPara two."
        chunks, _, _ = split_text(text, max_length=3500)
        assert len(chunks) == 1
        assert "Para one" in chunks[0] and "Para two" in chunks[0]

    def test_multiple_blank_lines_with_split(self):
        text = "Para one.\n\n\n\n\n\nPara two."
        chunks, _, _ = split_text(text, max_length=12)
        assert len(chunks) == 2
        assert all(c.strip() for c in chunks)

    def test_exact_max_length_paragraph_stays_one_chunk(self):
        para = "a" * 100
        chunks, _, _ = split_text(para, max_length=100)
        assert chunks == ["a" * 100]

    def test_whitespace_only_returns_empty(self):
        chunks, positions, sentences = split_text("   \n\n  \n\n")
        assert chunks == []
        assert positions == []
        assert sentences == []

    def test_long_no_punctuation_hard_splits_under_limit(self):
        text = "a" * 5000
        chunks, _, _ = split_text(text, max_length=4096)
        assert len(chunks) >= 2
        assert all(len(c) <= 4096 for c in chunks)
