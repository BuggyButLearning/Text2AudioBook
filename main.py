import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import datetime
import logging
import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, DISABLED, NORMAL, SECONDARY, SUCCESS, W

from text_processing import read_text_from_file, split_text
from tts_conversion import convert_text_to_speech, concatenate_audio_files, list_available_models
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
providers = ["OpenAI", "Ollama"]


def update_status(message):
    status_var.set(message)
    root.update_idletasks()


def set_controls_enabled(enabled):
    state = NORMAL if enabled else DISABLED
    browse_file_button.config(state=state)
    browse_output_button.config(state=state)
    refresh_models_button.config(state=state)
    start_button.config(state=state)


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
    models = list_available_models(provider, settings.openai_api_key, settings.ollama_base_url)
    if not models:
        model_var.set("")
        model_menu.configure(values=[])
        update_status(f"No {provider} models available")
        if provider == "Ollama":
            messagebox.showwarning(
                "No Ollama Models Found",
                "No local Ollama models were found. Ensure Ollama is running and models are installed.",
            )
        return

    model_menu.configure(values=models)
    model_var.set(models[0])
    update_status(f"Loaded {len(models)} {provider} models")


def on_provider_change(*_args):
    provider = provider_var.get()
    if provider == "OpenAI":
        voice_menu.config(state="readonly")
    else:
        voice_var.set("alloy")
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
    file_path = filedialog.askopenfilename(title="Select a Text File", filetypes=[("Text Files", "*.txt")])
    if file_path:
        file_entry.delete(0, tk.END)
        file_entry.insert(0, file_path)

def select_output_folder():
    folder_path = filedialog.askdirectory(title="Select Output Folder")
    if folder_path:
        folder_entry.delete(0, tk.END)
        folder_entry.insert(0, folder_path)

def start_conversion():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    input_file = file_entry.get()
    output_folder = folder_entry.get() or default_output_folder
    output_filename = sanitize_output_filename(output_name_entry.get())
    provider = provider_var.get()
    quality_preset = quality_var.get()
    model = model_var.get().strip()
    voice = voice_var.get()

    if not input_file or not output_filename or not model:
        messagebox.showerror("Error", "Please provide all required inputs")
        return

    settings = build_runtime_settings(
        provider=provider,
        quality_preset=quality_preset,
        model=model,
        voice=voice,
        output_folder=output_folder,
    )

    if provider == "OpenAI" and not settings.openai_api_key:
        messagebox.showerror("Error", "OpenAI API key is missing. Set OPENAI_API_KEY or use key.txt as a backup.")
        return

    set_controls_enabled(False)
    text = read_text_from_file(input_file)
    if not text:
        set_controls_enabled(True)
        messagebox.showerror("Error", "Failed to read the input text file.")
        return

    output_folder_path = Path(output_folder)
    output_folder_path.mkdir(parents=True, exist_ok=True)

    output_file = output_folder_path / f"{output_filename}.mp3"

    try:
        update_status("Preparing text...")
        text_chunks, positions, sentences = split_text(text)
        update_status(f"Converting {len(text_chunks)} chunk(s)...")
        audio_files = convert_text_to_speech(text_chunks, settings, output_folder_path, timestamp, status_callback=update_status)
        if len(audio_files) != len(text_chunks):
            raise RuntimeError("One or more chunks failed during text-to-speech conversion.")

        update_status("Merging audio...")
        concatenate_audio_files(audio_files, output_file)

        chunk_positions_file = output_folder_path / f"{output_filename}_chunk_positions.txt"
        with open(chunk_positions_file, 'w', encoding='utf-8') as f:
            for i, (position, sentence) in enumerate(zip(positions, sentences)):
                f.write(f"Chunk {i + 1} starts at character {position}: {sentence}\n")

        save_user_defaults(output_filename, output_folder_path)
        update_status("Conversion completed")
        messagebox.showinfo("Success", f"Conversion completed. Audio saved as {output_file}. Chunk positions saved as {chunk_positions_file}.")
    except Exception as exc:
        logging.exception("Conversion failed")
        update_status("Conversion failed")
        messagebox.showerror("Error", str(exc))
    finally:
        set_controls_enabled(True)

def create_app():
    global root, frame, file_entry, folder_entry, output_name_entry
    global provider_var, provider_menu, quality_var, quality_menu
    global model_var, model_menu, refresh_models_button, voice_var, voice_menu
    global status_var, browse_file_button, browse_output_button, start_button

    root = ttk.Window(themename="darkly")
    root.title("Text to Speech Converter")
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
    provider_menu = ttk.Combobox(frame, textvariable=provider_var, values=providers, state="readonly", width=28)
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
    return root


if __name__ == "__main__":
    app = create_app()
    app.mainloop()
