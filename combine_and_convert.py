import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import json
from pydub import AudioSegment
import os
import subprocess
import logging
import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, DISABLED, SECONDARY, SUCCESS, W

CONFIG_FILE = "config.json"

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to combine multiple audio files into one
def combine_audio_files(file_paths):
    combined = AudioSegment.empty()
    for file_path in file_paths:
        logging.debug(f"Combining file: {file_path}")
        audio = AudioSegment.from_mp3(file_path)
        combined += audio
    return combined

# Function to check if GPU encoding is available
def is_gpu_encoding_available():
    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders"], capture_output=True, text=True, check=True
        )
        available = "h264_nvenc" in result.stdout
        if not available:
            logging.warning("h264_nvenc not found in ffmpeg encoders.")
        return available
    except subprocess.CalledProcessError as e:
        logging.error(f"Error checking GPU encoding: {e}")
        return False

# Function to scale video if necessary
def scale_video(input_file, output_file, max_height=4096):
    try:
        logging.debug(f"Scaling video: {input_file} to max height: {max_height}")
        result = subprocess.run(
            ["ffmpeg", "-i", str(input_file), "-vf", f"scale=-2:{max_height}", str(output_file)],
            capture_output=True, text=True, check=True
        )
        logging.debug("Video scaled successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error scaling video: {e}")
        raise


def get_media_height(input_file):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=height",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(input_file),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        value = result.stdout.strip()
        return int(value) if value else None
    except Exception:
        return None


# Function to create a video file from the combined audio and an image
def create_video(audio_file, image_file, output_file, fps=24, max_height=4096):
    use_gpu = is_gpu_encoding_available()
    video_scaled_file = None
    height = get_media_height(image_file)
    if height and height > max_height:
        logging.debug(f"Image/video height {height} exceeds max height {max_height}, scaling required.")
        video_scaled_file = Path(output_file).with_suffix(".scaled.mp4")
        scale_video(image_file, video_scaled_file, max_height)
        image_file = video_scaled_file

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(image_file),
                "-i",
                str(audio_file),
                "-c:v",
                'h264_nvenc' if use_gpu else 'libx264',
                "-tune",
                "stillimage",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-pix_fmt",
                "yuv420p",
                "-shortest",
                "-r",
                str(fps),
                str(output_file),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception as e:
        logging.error(f"Video encoding failed. Error: {e}")
        messagebox.showerror("Error", f"Video encoding failed. Error: {e}")
        if use_gpu:
            logging.info("Falling back to CPU encoding.")
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    str(image_file),
                    "-i",
                    str(audio_file),
                    "-c:v",
                    "libx264",
                    "-tune",
                    "stillimage",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-pix_fmt",
                    "yuv420p",
                    "-shortest",
                    "-r",
                    str(fps),
                    str(output_file),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
    finally:
        if video_scaled_file and video_scaled_file.exists():
            os.remove(video_scaled_file)

def select_files():
    file_paths = filedialog.askopenfilenames(title="Select MP3 Files", filetypes=[("MP3 Files", "*.mp3")])
    if file_paths:
        listbox.delete(0, tk.END)  # Clear current listbox entries
        for file_path in file_paths:
            listbox.insert(tk.END, file_path)

def select_image():
    file_path = filedialog.askopenfilename(title="Select Background Image", filetypes=[("Image Files", "*.jpg;*.png")])
    if file_path:
        image_entry.delete(0, tk.END)
        image_entry.insert(0, file_path)

def select_output_folder():
    folder_path = filedialog.askdirectory(title="Select Output Folder")
    if folder_path:
        folder_entry.delete(0, tk.END)
        folder_entry.insert(0, folder_path)

def move_up():
    selected = listbox.curselection()
    if selected:
        for index in selected:
            if index > 0:
                file = listbox.get(index)
                listbox.delete(index)
                listbox.insert(index - 1, file)
                listbox.selection_set(index - 1)

def move_down():
    selected = listbox.curselection()
    if selected:
        for index in selected:
            if index < listbox.size() - 1:
                file = listbox.get(index)
                listbox.delete(index)
                listbox.insert(index + 1, file)
                listbox.selection_set(index + 1)

def start_conversion():
    mp3_files = listbox.get(0, tk.END)
    image_file = image_entry.get()
    output_folder = folder_entry.get()
    output_filename = output_name_entry.get().strip()

    if not mp3_files or not image_file or not output_folder or not output_filename:
        messagebox.showerror("Error", "Please provide all required inputs")
        return

    # Combine audio files
    combined_audio = combine_audio_files(mp3_files)
    combined_audio_file = Path(output_folder) / f"{output_filename}.mp3"
    combined_audio.export(str(combined_audio_file), format='mp3')

    # Create video file
    output_file = Path(output_folder) / f"{output_filename}.mp4"
    create_video(combined_audio_file, image_file, output_file)

    messagebox.showinfo("Success", f"Video file generated and saved to {output_file}")

    # Save the current inputs to config file
    save_config()

def save_config():
    config = {
        "mp3_files": list(listbox.get(0, tk.END)),
        "image_file": image_entry.get(),
        "output_folder": folder_entry.get(),
        "output_filename": output_name_entry.get().strip()
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            if "mp3_files" in config:
                listbox.delete(0, tk.END)
                for file_path in config["mp3_files"]:
                    listbox.insert(tk.END, file_path)
            if "image_file" in config:
                image_entry.delete(0, tk.END)
                image_entry.insert(0, config["image_file"])
            if "output_folder" in config:
                folder_entry.delete(0, tk.END)
                folder_entry.insert(0, config["output_folder"])
            if "output_filename" in config:
                output_name_entry.delete(0, tk.END)
                output_name_entry.insert(0, config["output_filename"])

def clear_fields():
    listbox.delete(0, tk.END)
    image_entry.delete(0, tk.END)
    folder_entry.delete(0, tk.END)
    output_name_entry.delete(0, tk.END)

def create_app():
    global root, frame, listbox_frame, scrollbar, listbox, image_entry, folder_entry, output_name_entry

    root = ttk.Window(themename="darkly")
    root.title("Combine MP3s and Convert to Video")
    root.geometry("760x520")

    frame = ttk.Frame(root, padding=18)
    frame.pack(fill=BOTH, expand=True)

    ttk.Label(frame, text="Audiobook Video Builder", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, columnspan=3, sticky=W, pady=(0, 10))
    ttk.Label(frame, text="Combine audio parts and generate a static-image video with FFmpeg.", bootstyle=SECONDARY).grid(row=1, column=0, columnspan=3, sticky=W, pady=(0, 12))

    listbox_frame = ttk.Frame(frame)
    listbox_frame.grid(row=2, column=0, columnspan=3, sticky="nsew")

    scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL)
    listbox = tk.Listbox(listbox_frame, selectmode=tk.SINGLE, width=50, height=10, yscrollcommand=scrollbar.set, bg="#1f1f1f", fg="#f5f5f5", relief="flat", highlightthickness=0)
    scrollbar.config(command=listbox.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    ttk.Button(frame, text="Browse MP3 Files", command=select_files, bootstyle=SECONDARY).grid(row=3, column=0, padx=5, pady=8, sticky=W)
    ttk.Button(frame, text="Move Up", command=move_up, bootstyle=SECONDARY).grid(row=3, column=1, padx=5, pady=8)
    ttk.Button(frame, text="Move Down", command=move_down, bootstyle=SECONDARY).grid(row=3, column=2, padx=5, pady=8, sticky="e")

    ttk.Label(frame, text="Background Image").grid(row=4, column=0, sticky=W, pady=6)
    image_entry = ttk.Entry(frame, width=50)
    image_entry.grid(row=4, column=1, padx=5, pady=6, sticky="ew")
    ttk.Button(frame, text="Browse", command=select_image, bootstyle=SECONDARY).grid(row=4, column=2, padx=5, pady=6)

    ttk.Label(frame, text="Output Folder").grid(row=5, column=0, sticky=W, pady=6)
    folder_entry = ttk.Entry(frame, width=50)
    folder_entry.grid(row=5, column=1, padx=5, pady=6, sticky="ew")
    ttk.Button(frame, text="Browse", command=select_output_folder, bootstyle=SECONDARY).grid(row=5, column=2, padx=5, pady=6)

    ttk.Label(frame, text="Output File Name").grid(row=6, column=0, sticky=W, pady=6)
    output_name_entry = ttk.Entry(frame, width=50)
    output_name_entry.grid(row=6, column=1, padx=5, pady=6, sticky="ew")

    ttk.Button(frame, text="Start Conversion", command=start_conversion, bootstyle=SUCCESS).grid(row=7, column=0, columnspan=2, pady=12, sticky="ew")
    ttk.Button(frame, text="Clear Fields", command=clear_fields, bootstyle=SECONDARY).grid(row=7, column=2, pady=12)

    load_config()
    return root


if __name__ == "__main__":
    app = create_app()
    app.mainloop()
