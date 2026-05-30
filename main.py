import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import datetime
import logging
import threading
import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, DISABLED, NORMAL, SECONDARY, SUCCESS, W

from model_discovery import discover_models, invalidate_cache, Source, DiscoveryResult
from providers import list_providers, get_provider_capability
from text_processing import read_text_from_file, split_text
from tts_conversion import convert_text_to_speech, concatenate_audio_files
from settings import (
    OPENAI_VOICES,
    QUALITY_PRESETS,
    build_runtime_settings,
    load_config,
    save_config,
    sanitize_output_filename,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize constants
script_directory = Path(__file__).parent
default_output_folder = script_directory / "output"
# Registry-driven so adding a provider in providers.py auto-shows in the dropdown.
# VibeVoice intentionally absent from PROVIDER_REGISTRY (v0.2); do not hardcode here.
provider_options = list(list_providers())


_VALIDATION_LABELS = {
    "input_file": "Input File",
    "output_filename": "Output File Name",
    "model": "Model",
}


def _validate_conversion_inputs(input_file, output_filename, model):
    """Return (ok, missing) where missing is the list of friendly field labels
    that are empty/whitespace. Pure-Python -- no Tk dependency."""
    fields = {
        "input_file": (input_file or "").strip(),
        "output_filename": (output_filename or "").strip(),
        "model": (model or "").strip(),
    }
    missing = [_VALIDATION_LABELS[k] for k, v in fields.items() if not v]
    return (len(missing) == 0, missing)


def _format_discovery_status(result):
    """Map a DiscoveryResult to a status-label string. Pure-Python."""
    provider = result.provider
    count = len(result.models)
    if result.source == Source.LIVE:
        return f"Loaded {count} {provider} model{'s' if count != 1 else ''}"
    if result.source == Source.EMPTY:
        reason = f" -- {result.error}" if result.error else ""
        return f"No {provider} models available{reason}"
    # FALLBACK with no error == provider has no live-probe path (e.g. local-hf
    # Kokoro before Phase 6.2). FALLBACK with error == live probe failed.
    if result.error is None:
        return f"{provider}: using registry list ({count} model{'s' if count != 1 else ''})"
    return f"{provider} discovery failed ({result.error}) -- using fallback list"


# Audit-added S1: prevents fast-double-click on Start from spawning two workers.
# Single-threaded Tk event loop makes the read-check-set atomic; no lock needed.
_conversion_in_progress = False


def update_status(message):
    status_var.set(message)
    root.update_idletasks()


def _thread_safe_status(message):
    """Marshal status updates from a worker thread back to the Tk main thread.

    Tkinter on Windows enforces a strict main-thread-only invariant on widget
    writes; calling `status_var.set(...)` directly from a worker thread can
    crash the interpreter or produce silent state corruption. `root.after(0, ...)`
    queues the callback into Tk's main event loop, which then executes it on
    the main thread at the next idle.

    Contract: this helper MUST be the ONLY status-update path used by code
    running in a non-main thread. Direct widget writes from worker threads
    are forbidden (audit-added S3).

    The RuntimeError catch handles the race where the window is destroyed
    mid-conversion while a status update is in-flight.
    """
    try:
        root.after(0, lambda: status_var.set(message))
    except RuntimeError:
        logging.debug("status update skipped: Tk root not available")


def _provider_has_voices(provider_name):
    cap = get_provider_capability(provider_name)
    return bool(cap and cap.voices)


def set_controls_enabled(enabled):
    state = NORMAL if enabled else DISABLED
    combobox_state = "readonly" if enabled else DISABLED
    browse_file_button.config(state=state)
    browse_output_button.config(state=state)
    refresh_models_button.config(state=state)
    start_button.config(state=state)
    # Phase 4: dropdowns also get locked so users can't change provider/model/etc.
    # mid-conversion (which would leave the runtime settings inconsistent).
    provider_menu.config(state=combobox_state)
    quality_menu.config(state=combobox_state)
    model_menu.config(state=combobox_state)
    # voice_menu: registry-driven. Provider with voices=() (e.g. Ollama) -> disabled.
    if enabled and _provider_has_voices(provider_var.get()):
        voice_menu.config(state="readonly")
    else:
        voice_menu.config(state=DISABLED)


def load_ui_defaults():
    config = load_config()
    provider_var.set(config.get("default_provider") or "OpenAI")
    quality_var.set(config.get("default_quality_preset") or "Balanced")
    output_name_entry.delete(0, tk.END)
    output_name_entry.insert(0, config.get("output_filename") or "audiobook")


def refresh_models():
    provider = provider_var.get()
    settings = build_runtime_settings(provider=provider)
    update_status(f"Refreshing {provider} models...")
    # Phase 4: invalidate the per-provider cache so "Refresh" truly refreshes.
    invalidate_cache(provider)
    result = discover_models(
        provider,
        api_key=settings.openai_api_key,
        ollama_base_url=settings.ollama_base_url,
        use_cache=False,
    )
    models = list(result.models)
    if not models:
        model_var.set("")
        model_menu.configure(values=[])
        update_status(_format_discovery_status(result))
        if provider == "Ollama" and result.source == Source.EMPTY:
            messagebox.showwarning(
                "No Ollama Models Found",
                "No local Ollama models matched the curated allowlist. Ensure Ollama is "
                "running and a TTS-capable model is installed (bark, kokoro, tts-*, speech-*).",
            )
        return

    model_menu.configure(values=models)
    model_var.set(models[0])
    update_status(_format_discovery_status(result))


def on_provider_change(*_args):
    provider = provider_var.get()
    cap = get_provider_capability(provider)
    voices = list(cap.voices) if cap else []
    if voices:
        voice_menu.configure(values=voices)
        # Preserve current selection if still valid; otherwise pick the first voice.
        if voice_var.get() not in voices:
            voice_var.set(voices[0])
        voice_menu.config(state="readonly")
    else:
        voice_menu.configure(values=[])
        voice_var.set("")
        voice_menu.config(state=DISABLED)
    refresh_models()


def save_user_defaults(output_filename, output_folder):
    config = load_config()
    config.update(
        {
            "default_provider": provider_var.get(),
            "default_quality_preset": quality_var.get(),
            "default_model": model_var.get(),
            "default_voice": voice_var.get(),
            "output_folder": str(output_folder),
            "output_filename": output_filename,
        }
    )
    save_config(config)

def select_file():
    file_path = filedialog.askopenfilename(
        title="Select a Text or Markdown File",
        filetypes=[
            ("Text and Markdown", "*.txt *.md *.markdown"),
            ("Text Files", "*.txt"),
            ("Markdown", "*.md *.markdown"),
            ("All Files", "*.*"),
        ],
    )
    if file_path:
        file_entry.delete(0, tk.END)
        file_entry.insert(0, file_path)

def select_output_folder():
    folder_path = filedialog.askdirectory(title="Select Output Folder")
    if folder_path:
        folder_entry.delete(0, tk.END)
        folder_entry.insert(0, folder_path)

def start_conversion():
    global _conversion_in_progress
    # Audit-added S1: discard fast-double-click spawn. No error to the user;
    # the in-flight conversion is the right thing to be running.
    if _conversion_in_progress:
        return

    input_file = file_entry.get()
    output_folder = folder_entry.get() or default_output_folder
    output_filename = sanitize_output_filename(output_name_entry.get())
    provider = provider_var.get()
    quality_preset = quality_var.get()
    model = model_var.get().strip()
    voice = voice_var.get()

    ok, missing = _validate_conversion_inputs(input_file, output_filename, model)
    if not ok:
        messagebox.showerror("Error", f"Please provide: {', '.join(missing)}")
        return

    settings = build_runtime_settings(
        provider=provider,
        quality_preset=quality_preset,
        model=model,
        voice=voice,
        output_folder=output_folder,
    )

    if provider == "OpenAI" and not settings.openai_api_key:
        messagebox.showerror(
            "Error",
            "OpenAI API key is missing. Set OPENAI_API_KEY or use key.txt as a backup.",
        )
        return

    # Phase 6.2: only HARD blocker for Kokoro is the python package.
    # Verified 2026-05-22 that American-English synthesis works without
    # espeak-ng on PATH; see kokoro_synthesis.kokoro_ready docstring.
    if provider == "Kokoro":
        from kokoro_synthesis import kokoro_available, install_kokoro_runtime
        lib_ok, _ = kokoro_available()
        if not lib_ok:
            if not messagebox.askyesno(
                "Install Kokoro now?",
                "Kokoro requires the `kokoro` Python package plus the Kokoro-82M model "
                "weights (~500 MB on first download to ~/.cache/huggingface).\n\n"
                "Install now? This may take a few minutes.",
            ):
                return
            _conversion_in_progress = True
            set_controls_enabled(False)
            installer = threading.Thread(
                target=_run_kokoro_installer,
                args=(install_kokoro_runtime,),
                daemon=True,
            )
            installer.start()
            return

    # Audit-added S1: set guard BEFORE any UI state changes so the next click is rejected.
    _conversion_in_progress = True
    set_controls_enabled(False)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder_path = Path(output_folder)
    output_filename_local = output_filename

    # Phase 4: run synthesis on a background thread so the Tk event loop stays
    # responsive (window draggable, status label visibly tick). Status callbacks
    # are marshaled back to the main thread via _thread_safe_status.
    worker = threading.Thread(
        target=_run_conversion_worker,
        args=(input_file, output_folder_path, output_filename_local, settings, timestamp),
        daemon=True,
    )
    worker.start()


def _run_kokoro_installer(install_fn):
    """Background-thread worker for one-click Kokoro install. Marshals status
    updates + final dialog back to the Tk main thread via root.after(0, ...).
    Resets _conversion_in_progress + re-enables controls in finally."""
    try:
        ok, reason = install_fn(progress_callback=_thread_safe_status)
        if ok:
            root.after(0, lambda: messagebox.showinfo(
                "Kokoro installed",
                "Kokoro runtime ready. Click Start Conversion to synthesize.",
            ))
            _thread_safe_status("Kokoro runtime ready")
        else:
            root.after(0, lambda r=reason: messagebox.showerror(
                "Kokoro install failed", r or "unknown error",
            ))
            _thread_safe_status("Kokoro install failed")
    except Exception as exc:
        logging.exception("kokoro installer raised")
        root.after(0, lambda exc=exc: messagebox.showerror(
            "Kokoro install failed", str(exc),
        ))
        _thread_safe_status("Kokoro install failed")
    finally:
        def _reset_state():
            global _conversion_in_progress
            _conversion_in_progress = False
            set_controls_enabled(True)
        root.after(0, _reset_state)


def _run_conversion_worker(input_file, output_folder_path, output_filename, settings, timestamp):
    """Background-thread worker. Uses _thread_safe_status for all GUI updates."""
    try:
        output_folder_path.mkdir(parents=True, exist_ok=True)
        output_file = output_folder_path / f"{output_filename}.mp3"

        _thread_safe_status("Reading input...")
        text = read_text_from_file(input_file)
        if not text:
            root.after(0, lambda: messagebox.showerror("Error", "Failed to read the input text file."))
            _thread_safe_status("Failed to read input")
            return

        _thread_safe_status("Preparing text...")
        chunk_max = getattr(settings, "chunk_max", None)
        if chunk_max:
            text_chunks, positions, sentences = split_text(text, max_length=chunk_max)
        else:
            text_chunks, positions, sentences = split_text(text)
        _thread_safe_status(f"Converting {len(text_chunks)} chunk(s)...")
        audio_files = convert_text_to_speech(
            text_chunks, settings, output_folder_path, timestamp,
            status_callback=_thread_safe_status,
        )
        if len(audio_files) != len(text_chunks):
            raise RuntimeError("One or more chunks failed during text-to-speech conversion.")

        _thread_safe_status("Merging audio...")
        concatenate_audio_files(audio_files, output_file)

        chunk_positions_file = output_folder_path / f"{output_filename}_chunk_positions.txt"
        with open(chunk_positions_file, 'w', encoding='utf-8') as f:
            for i, (position, sentence) in enumerate(zip(positions, sentences)):
                f.write(f"Chunk {i + 1} starts at character {position}: {sentence}\n")

        root.after(0, lambda: save_user_defaults(output_filename, output_folder_path))
        _thread_safe_status("Conversion completed")
        root.after(0, lambda: messagebox.showinfo(
            "Success",
            f"Conversion completed. Audio saved as {output_file}. "
            f"Chunk positions saved as {chunk_positions_file}.",
        ))
    except Exception as exc:
        logging.exception("Conversion failed")
        _thread_safe_status("Conversion failed")
        # Capture exc in default-arg to avoid late-binding in the lambda.
        root.after(0, lambda exc=exc: messagebox.showerror("Error", str(exc)))
    finally:
        # Audit-added S1: clear the guard so the user can start a new conversion.
        def _reset_state():
            global _conversion_in_progress
            _conversion_in_progress = False
            set_controls_enabled(True)
        root.after(0, _reset_state)

def create_app():
    global root, frame, file_entry, folder_entry, output_name_entry
    global provider_var, provider_menu, quality_var, quality_menu
    global model_var, model_menu, refresh_models_button, voice_var, voice_menu
    global status_var, browse_file_button, browse_output_button, start_button

    root = ttk.Window(themename="darkly")
    root.title("Text to Speech Converter")
    # Initial geometry is overridden by _autosize_window after widgets are laid out.
    root.geometry("760x420")
    root.minsize(720, 390)

    frame = ttk.Frame(root, padding=18)
    frame.pack(fill=BOTH, expand=True)

    ttk.Label(frame, text="Text2AudioBook", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, columnspan=3, sticky=W, pady=(0, 10))
    ttk.Label(frame, text="Convert text into audio with OpenAI or local Ollama model discovery.", bootstyle=SECONDARY).grid(row=1, column=0, columnspan=3, sticky=W, pady=(0, 14))

    ttk.Label(frame, text="Input Text File").grid(row=2, column=0, sticky=W, pady=6)
    file_entry = ttk.Entry(frame, width=58)
    file_entry.grid(row=2, column=1, padx=8, pady=6, sticky="ew")
    browse_file_button = ttk.Button(frame, text="Browse", command=select_file, bootstyle=SECONDARY)
    browse_file_button.grid(row=2, column=2, padx=5, pady=6)

    ttk.Label(frame, text="Output Folder").grid(row=3, column=0, sticky=W, pady=6)
    folder_entry = ttk.Entry(frame, width=58)
    folder_entry.insert(0, str(default_output_folder))
    folder_entry.grid(row=3, column=1, padx=8, pady=6, sticky="ew")
    browse_output_button = ttk.Button(frame, text="Browse", command=select_output_folder, bootstyle=SECONDARY)
    browse_output_button.grid(row=3, column=2, padx=5, pady=6)

    ttk.Label(frame, text="Output File Name").grid(row=4, column=0, sticky=W, pady=6)
    output_name_entry = ttk.Entry(frame, width=58)
    output_name_entry.grid(row=4, column=1, padx=8, pady=6, sticky="ew")

    ttk.Label(frame, text="Provider").grid(row=5, column=0, sticky=W, pady=6)
    provider_var = tk.StringVar(value="OpenAI")
    provider_menu = ttk.Combobox(frame, textvariable=provider_var, values=provider_options, state="readonly", width=28)
    provider_menu.grid(row=5, column=1, padx=8, pady=6, sticky=W)

    ttk.Label(frame, text="Quality Preset").grid(row=6, column=0, sticky=W, pady=6)
    quality_var = tk.StringVar(value="Balanced")
    quality_menu = ttk.Combobox(frame, textvariable=quality_var, values=list(QUALITY_PRESETS.keys()), state="readonly", width=28)
    quality_menu.grid(row=6, column=1, padx=8, pady=6, sticky=W)

    ttk.Label(frame, text="Model").grid(row=7, column=0, sticky=W, pady=6)
    model_var = tk.StringVar(value="tts-1")
    model_menu = ttk.Combobox(frame, textvariable=model_var, values=["tts-1"], state="readonly", width=28)
    model_menu.grid(row=7, column=1, padx=8, pady=6, sticky=W)
    refresh_models_button = ttk.Button(frame, text="Refresh Models", command=refresh_models, bootstyle=SECONDARY)
    refresh_models_button.grid(row=7, column=2, padx=5, pady=6)

    ttk.Label(frame, text="Voice").grid(row=8, column=0, sticky=W, pady=6)
    voice_var = tk.StringVar(value="alloy")
    voice_menu = ttk.Combobox(frame, textvariable=voice_var, values=OPENAI_VOICES, state="readonly", width=28)
    voice_menu.grid(row=8, column=1, padx=8, pady=6, sticky=W)

    status_var = tk.StringVar(value="Idle")
    ttk.Separator(frame).grid(row=9, column=0, columnspan=3, sticky="ew", pady=(12, 10))
    ttk.Label(frame, textvariable=status_var, anchor="w", bootstyle=SECONDARY).grid(row=10, column=0, columnspan=3, sticky=W, pady=(0, 10))

    start_button = ttk.Button(frame, text="Start Conversion", command=start_conversion, bootstyle=SUCCESS)
    start_button.grid(row=11, column=0, columnspan=3, pady=10, sticky="ew")

    frame.grid_columnconfigure(1, weight=1)

    provider_var.trace_add("write", on_provider_change)
    load_ui_defaults()
    refresh_models()
    _autosize_window(root)
    return root


def _autosize_window(window, padding_w=24, padding_h=24, min_w=720, min_h=390):
    """Resize window to exactly the requested size of its content, plus a small
    padding so dropdown chevrons and the status label aren't clipped. Enforces a
    floor (min_w x min_h) so the layout never collapses when the theme reports
    a smaller-than-comfortable reqsize.
    """
    window.update_idletasks()
    req_w = max(window.winfo_reqwidth() + padding_w, min_w)
    req_h = max(window.winfo_reqheight() + padding_h, min_h)
    window.geometry(f"{req_w}x{req_h}")
    window.minsize(req_w, req_h)


if __name__ == "__main__":
    app = create_app()
    app.mainloop()
