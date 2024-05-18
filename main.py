import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import datetime
import logging
from text_processing import read_text_from_file, split_text
from tts_conversion import convert_text_to_speech, concatenate_audio_files

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to read API key from key.txt
def read_api_key(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.readline().strip()  # Reads the first line and removes any leading/trailing whitespace
    except Exception as e:
        logging.error(f"Error reading the API key file: {e}")
        return None

# Initialize constants
script_directory = Path(__file__).parent
OPENAI_API_KEY = read_api_key(script_directory / "key.txt")
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
default_output_folder = script_directory / "output"

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
    input_file = file_entry.get()
    output_folder = folder_entry.get() or default_output_folder
    output_filename = output_name_entry.get().strip()
    voice = voice_var.get()

    if not input_file or not output_filename or not voice:
        messagebox.showerror("Error", "Please provide all required inputs")
        return

    if not OPENAI_API_KEY:
        messagebox.showerror("Error", "OpenAI API key is missing. Please ensure key.txt contains the API key.")
        return

    text = read_text_from_file(input_file)
    if not text:
        messagebox.showerror("Error", "Failed to read the input text file.")
        return

    # Ensure the output folder exists
    output_folder_path = Path(output_folder)
    output_folder_path.mkdir(parents=True, exist_ok=True)

    output_file = output_folder_path / f"{output_filename}.mp3"

    text_chunks, positions, sentences = split_text(text)
    audio_files = convert_text_to_speech(text_chunks, OPENAI_API_KEY, voice, output_folder_path, timestamp)
    if not audio_files:
        messagebox.showerror("Error", "Text-to-speech conversion failed.")
        return

    concatenate_audio_files(audio_files, output_file)

    # Creating the chunk positions text file
    chunk_positions_file = output_folder_path / f"{output_filename}_chunk_positions.txt"
    with open(chunk_positions_file, 'w', encoding='utf-8') as f:
        for i, (position, sentence) in enumerate(zip(positions, sentences)):
            f.write(f"Chunk {i + 1} starts at character {position}: {sentence}\n")
    messagebox.showinfo("Success", f"Conversion completed. Audio saved as {output_file}. Chunk positions saved as {chunk_positions_file}.")

# Create GUI
root = tk.Tk()
root.title("Text to Speech Converter")

frame = tk.Frame(root, padx=10, pady=10)
frame.pack(padx=10, pady=10)

tk.Label(frame, text="Input Text File:").grid(row=0, column=0, sticky=tk.W)
file_entry = tk.Entry(frame, width=50)
file_entry.grid(row=0, column=1, padx=5, pady=5)
tk.Button(frame, text="Browse...", command=select_file).grid(row=0, column=2, padx=5, pady=5)

tk.Label(frame, text="Output Folder:").grid(row=1, column=0, sticky=tk.W)
folder_entry = tk.Entry(frame, width=50)
folder_entry.insert(0, str(default_output_folder))  # Set default output folder
folder_entry.grid(row=1, column=1, padx=5, pady=5)
tk.Button(frame, text="Browse...", command=select_output_folder).grid(row=1, column=2, padx=5, pady=5)

tk.Label(frame, text="Output File Name (without extension):").grid(row=2, column=0, sticky=tk.W)
output_name_entry = tk.Entry(frame, width=50)
output_name_entry.grid(row=2, column=1, padx=5, pady=5)

tk.Label(frame, text="Select Voice:").grid(row=3, column=0, sticky=tk.W)
voice_var = tk.StringVar(value="alloy")
voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
tk.OptionMenu(frame, voice_var, *voices).grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

tk.Button(frame, text="Start Conversion", command=start_conversion).grid(row=4, column=0, columnspan=3, pady=10)

root.mainloop()
