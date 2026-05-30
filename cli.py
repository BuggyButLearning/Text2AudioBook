"""
Text2AudioBook CLI (Phase 8).

Machine-callable entry point. Every GUI setting overridable via flags. Stable
exit codes. `--json` JSON Lines output for AI agents. See docs/CLI.md.

Invoke:
    python -m text2audiobook <command> [options]
    python cli.py <command> [options]
"""
import argparse
import datetime
import json
import logging
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_INVALID_ARGS = 1
EXIT_SYNTHESIS_FAILED = 2
EXIT_PROVIDER_NOT_READY = 3
EXIT_INPUT_UNREADABLE = 4


def _emit(json_mode, payload, human_fallback=None, file=None):
    """Write a JSON Lines record to stdout (json_mode) or a human line."""
    stream = file or sys.stdout
    if json_mode:
        stream.write(json.dumps(payload) + "\n")
    elif human_fallback is not None:
        stream.write(human_fallback + "\n")
    stream.flush()


def cmd_list_providers(args):
    from providers import list_providers
    names = list(list_providers())
    if args.json:
        _emit(True, {"providers": names})
    else:
        print("\n".join(names))
    return EXIT_OK


def cmd_list_voices(args):
    from providers import get_provider_capability
    cap = get_provider_capability(args.provider)
    if cap is None:
        _emit(args.json, {"error": f"unknown provider: {args.provider}"},
              f"unknown provider: {args.provider}", file=sys.stderr)
        return EXIT_INVALID_ARGS
    voices = list(cap.voices)
    if args.json:
        _emit(True, {"provider": args.provider, "voices": voices})
    else:
        if voices:
            print("\n".join(voices))
        else:
            print(f"(no voices for {args.provider})")
    return EXIT_OK


def cmd_list_models(args):
    from model_discovery import discover_models, invalidate_cache
    if args.refresh:
        invalidate_cache(args.provider)
    result = discover_models(
        args.provider,
        api_key=args.openai_api_key,
        ollama_base_url=args.ollama_base_url,
        use_cache=not args.refresh,
    )
    models = list(result.models)
    if args.json:
        _emit(True, {
            "provider": args.provider,
            "models": models,
            "source": result.source.value,
            "error": result.error,
        })
    else:
        for m in models:
            print(m)
        if result.error:
            print(f"# note ({result.source.value}): {result.error}", file=sys.stderr)
    return EXIT_OK


def cmd_chunk_policy(args):
    from chunk_policy import policy_snapshot, resolve_chunk_max
    from settings import load_config
    overrides = (load_config().get("chunk_overrides") or {})
    snap = policy_snapshot(overrides=overrides)
    if args.provider:
        resolved = resolve_chunk_max(args.provider, model=args.model, overrides=overrides)
        snap["resolved"] = {"provider": args.provider, "model": args.model, "chunk_max": resolved}
    if args.json:
        _emit(True, snap)
    else:
        print("Built-in defaults:")
        for p, n in snap["policy"].items():
            print(f"  {p:10s} {n}")
        print(f"Fallback: {snap['fallback']}")
        if snap["overrides"]:
            print("Config overrides:")
            for k, v in snap["overrides"].items():
                print(f"  {k:20s} {v}")
        if "resolved" in snap:
            r = snap["resolved"]
            print(f"Resolved for {r['provider']}"
                  f"{':' + r['model'] if r['model'] else ''} -> {r['chunk_max']}")
    return EXIT_OK


def cmd_show_config(args):
    from settings import build_runtime_settings
    s = build_runtime_settings(
        provider=args.provider, quality_preset=args.quality,
        model=args.model, voice=args.voice,
    )
    snap = {
        "provider": s.provider, "quality_preset": s.quality_preset,
        "model": s.model, "voice": s.voice, "speed": s.speed,
        "output_folder": str(s.output_folder),
        "ollama_base_url": s.ollama_base_url,
        "max_concurrency": s.max_concurrency,
        "response_format": s.response_format,
        "chunk_max": s.chunk_max,
        "openai_api_key_present": bool(s.openai_api_key),
    }
    if args.json:
        _emit(True, snap)
    else:
        for k, v in snap.items():
            print(f"{k:25s} {v}")
    return EXIT_OK


def cmd_synthesize(args):
    from settings import build_runtime_settings, sanitize_output_filename
    from text_processing import read_text_from_file, split_text
    from tts_conversion import convert_text_to_speech, concatenate_audio_files

    input_path = Path(args.input)
    if not input_path.exists():
        _emit(args.json, {"event": "error", "stage": "input", "message": f"input file not found: {input_path}"},
              f"input file not found: {input_path}", file=sys.stderr)
        return EXIT_INPUT_UNREADABLE

    output_path = Path(args.output)
    output_folder = output_path.parent or Path(".")
    output_filename = sanitize_output_filename(output_path.stem)
    if not output_filename:
        _emit(args.json, {"event": "error", "stage": "validation", "message": "output filename empty after sanitization"},
              "output filename empty after sanitization", file=sys.stderr)
        return EXIT_INVALID_ARGS

    settings = build_runtime_settings(
        provider=args.provider, quality_preset=args.quality,
        model=args.model, voice=args.voice,
        output_folder=output_folder,
        chunk_max=args.chunk_max,
    )
    if args.speed is not None:
        settings.speed = args.speed
    if args.max_concurrency is not None:
        settings.max_concurrency = args.max_concurrency
    if args.openai_api_key:
        settings.openai_api_key = args.openai_api_key
    if args.ollama_base_url:
        settings.ollama_base_url = args.ollama_base_url

    if settings.provider == "OpenAI" and not settings.openai_api_key:
        _emit(args.json, {"event": "error", "stage": "validation", "message": "OPENAI_API_KEY not set"},
              "OpenAI API key missing. Set OPENAI_API_KEY or use key.txt.", file=sys.stderr)
        return EXIT_INVALID_ARGS

    if settings.provider == "Kokoro":
        from kokoro_synthesis import kokoro_available
        ok, reason = kokoro_available()
        if not ok:
            _emit(args.json, {"event": "error", "stage": "provider", "message": reason},
                  f"Kokoro not ready: {reason}", file=sys.stderr)
            return EXIT_PROVIDER_NOT_READY

    text = read_text_from_file(str(input_path))
    if not text:
        _emit(args.json, {"event": "error", "stage": "input", "message": "input file empty or unreadable"},
              "input file empty or unreadable", file=sys.stderr)
        return EXIT_INPUT_UNREADABLE

    chunks, positions, sentences = split_text(text, max_length=settings.chunk_max or 3500)
    plan = {
        "event": "start",
        "provider": settings.provider, "model": settings.model, "voice": settings.voice,
        "chunks": len(chunks), "chunk_max": settings.chunk_max,
        "output": str(output_path),
    }
    if args.dry_run:
        plan["event"] = "dry-run"
        _emit(args.json, plan,
              f"DRY RUN -> provider={settings.provider} model={settings.model} "
              f"voice={settings.voice} chunks={len(chunks)} chunk_max={settings.chunk_max} "
              f"output={output_path}")
        return EXIT_OK

    _emit(args.json, plan,
          f"Synthesizing {len(chunks)} chunk(s) via {settings.provider}/{settings.model}...")

    output_folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    started = datetime.datetime.now()

    def _status_cb(msg):
        if not args.quiet:
            _emit(args.json, {"event": "status", "message": msg}, msg)

    audio_files = convert_text_to_speech(
        chunks, settings, output_folder, timestamp, status_callback=_status_cb,
    )
    if len(audio_files) != len(chunks):
        _emit(args.json,
              {"event": "error", "stage": "synthesis",
               "message": f"only {len(audio_files)}/{len(chunks)} chunks succeeded"},
              f"synthesis failed: only {len(audio_files)}/{len(chunks)} chunks succeeded",
              file=sys.stderr)
        return EXIT_SYNTHESIS_FAILED

    concatenate_audio_files(audio_files, output_path)
    duration_ms = int((datetime.datetime.now() - started).total_seconds() * 1000)
    _emit(args.json,
          {"event": "complete", "output": str(output_path), "duration_ms": duration_ms,
           "chunks": len(chunks)},
          f"Conversion completed -> {output_path} ({duration_ms} ms)")
    return EXIT_OK


def build_parser():
    p = argparse.ArgumentParser(
        prog="text2audiobook",
        description="Multi-provider TTS CLI. See docs/CLI.md for full reference.",
    )
    p.add_argument("--json", action="store_true", help="emit JSON Lines instead of human text")
    # required=False so empty argv falls through to the help branch in main()
    # instead of argparse emitting "the following arguments are required: command"
    # with exit code 2. New users / agents probing the CLI deserve friendly help.
    sub = p.add_subparsers(dest="command", required=False)

    sp = sub.add_parser("list-providers", help="list registered providers")
    sp.set_defaults(func=cmd_list_providers)

    sv = sub.add_parser("list-voices", help="list voices for a provider")
    sv.add_argument("--provider", required=True)
    sv.set_defaults(func=cmd_list_voices)

    sm = sub.add_parser("list-models", help="list models (live discovery) for a provider")
    sm.add_argument("--provider", required=True)
    sm.add_argument("--refresh", action="store_true", help="invalidate cache before discovery")
    sm.add_argument("--openai-api-key", default=None)
    sm.add_argument("--ollama-base-url", default=None)
    sm.set_defaults(func=cmd_list_models)

    cp = sub.add_parser("chunk-policy", help="show built-in chunk_max defaults + overrides")
    cp.add_argument("--provider", default=None, help="resolve effective chunk_max for this provider")
    cp.add_argument("--model", default=None, help="resolve effective chunk_max for this model")
    cp.set_defaults(func=cmd_chunk_policy)

    sc = sub.add_parser("show-config", help="dump effective runtime settings")
    sc.add_argument("--provider", default=None)
    sc.add_argument("--quality", default=None)
    sc.add_argument("--model", default=None)
    sc.add_argument("--voice", default=None)
    sc.set_defaults(func=cmd_show_config)

    sy = sub.add_parser("synthesize", help="convert text/markdown -> mp3")
    sy.add_argument("--input", required=True, help="path to .txt / .md / .markdown")
    sy.add_argument("--output", required=True, help="path to .mp3 output")
    sy.add_argument("--provider", default=None)
    sy.add_argument("--model", default=None)
    sy.add_argument("--voice", default=None)
    sy.add_argument("--quality", default=None, choices=["Balanced", "Best Quality", "Fast"])
    sy.add_argument("--chunk-max", type=int, default=None, help="override per-provider chunk_max")
    sy.add_argument("--speed", type=float, default=None)
    sy.add_argument("--max-concurrency", type=int, default=None)
    sy.add_argument("--openai-api-key", default=None)
    sy.add_argument("--ollama-base-url", default=None)
    sy.add_argument("--quiet", action="store_true", help="suppress per-status output")
    sy.add_argument("--dry-run", action="store_true", help="validate + plan, don't synthesize")
    sy.set_defaults(func=cmd_synthesize)

    return p


def main(argv=None):
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    if argv is None:
        argv = sys.argv[1:]
    # Translate standalone `?` tokens into `-h`. List comparison (not string
    # contains) so paths like --input "foo?.txt" pass through untouched.
    argv = ["-h" if a == "?" else a for a in argv]
    parser = build_parser()
    if not argv:
        parser.print_help()
        return EXIT_OK
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_OK
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
