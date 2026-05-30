"""Phase 9 — CLI help-on-no-args + `?` alias.

Locks the friendly-failure behavior added in cli.py: empty argv prints help
and exits 0, `?` translates to `-h` and works both as the sole argument and
after a subcommand.
"""
import io
import sys

import pytest

import cli


def _run(argv, monkeypatch):
    """Reuses the pattern from tests/test_cli.py; argparse `-h` calls sys.exit
    so we must catch SystemExit and treat code 0 as success."""
    buf_out, buf_err = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf_out)
    monkeypatch.setattr(sys, "stderr", buf_err)
    try:
        code = cli.main(argv)
    except SystemExit as e:
        code = e.code if e.code is not None else 0
    return code, buf_out.getvalue(), buf_err.getvalue()


class TestNoArgsHelp:
    def test_empty_argv_prints_help_exits_0(self, monkeypatch):
        code, out, _err = _run([], monkeypatch)
        assert code == cli.EXIT_OK
        assert "usage:" in out.lower()

    def test_empty_argv_lists_all_subcommands(self, monkeypatch):
        _code, out, _err = _run([], monkeypatch)
        for sub in ["list-providers", "list-voices", "list-models",
                    "chunk-policy", "show-config", "synthesize"]:
            assert sub in out, f"subcommand {sub!r} missing from help"

    def test_no_args_does_NOT_print_argparse_error(self, monkeypatch):
        """Regression guard: before this change, no-args exited 2 with
        'the following arguments are required: command'."""
        _code, _out, err = _run([], monkeypatch)
        assert "required" not in err.lower()


class TestQuestionMarkAlias:
    def test_lone_question_mark_prints_help_exits_0(self, monkeypatch):
        code, out, _err = _run(["?"], monkeypatch)
        assert code == cli.EXIT_OK
        assert "usage:" in out.lower()

    def test_question_mark_after_subcommand_prints_subcommand_help(self, monkeypatch):
        code, out, _err = _run(["list-providers", "?"], monkeypatch)
        assert code == cli.EXIT_OK
        # Subcommand help mentions the subcommand name.
        assert "list-providers" in out

    def test_question_mark_after_synthesize_prints_synth_help(self, monkeypatch):
        code, out, _err = _run(["synthesize", "?"], monkeypatch)
        assert code == cli.EXIT_OK
        # synthesize help should mention some of its required flags.
        assert "--input" in out
        assert "--output" in out


class TestQuestionMarkDoesNotMutateRealArgs:
    """The `?` translation operates on list elements (a == "?"), NOT
    on string contents. Paths like `--input foo?.txt` must pass through
    untouched and be received by argparse intact."""

    def test_question_mark_inside_path_arg_untouched(self, monkeypatch, tmp_path):
        # The path won't exist so we expect EXIT_INPUT_UNREADABLE -- but the
        # important assertion is that argparse parsed the arg as-is (no help shown).
        nonexistent = str(tmp_path / "foo?.txt")
        out_path = tmp_path / "out.mp3"
        code, _out, err = _run([
            "synthesize", "--input", nonexistent, "--output", str(out_path),
            "--provider", "OpenAI",
        ], monkeypatch)
        # Should be input-unreadable (4), NOT help/help-no-args (0)
        assert code == cli.EXIT_INPUT_UNREADABLE
        # Stderr should mention 'not found', confirming arg made it through.
        assert "not found" in err.lower()


class TestDashHStillWorks:
    """Regression guard: the existing -h / --help short flags still exit 0
    with help output. argparse handles these via SystemExit(0)."""

    def test_dash_h_top_level(self, monkeypatch):
        code, out, _err = _run(["-h"], monkeypatch)
        assert code == 0
        assert "usage:" in out.lower()

    def test_dash_dash_help_top_level(self, monkeypatch):
        code, out, _err = _run(["--help"], monkeypatch)
        assert code == 0
        assert "usage:" in out.lower()

    def test_dash_h_on_subcommand(self, monkeypatch):
        code, out, _err = _run(["synthesize", "-h"], monkeypatch)
        assert code == 0
        assert "--input" in out
