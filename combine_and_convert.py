import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import json
from pydub import AudioSegment
from moviepy.editor import ImageClip, AudioFileClip, VideoFileClip
import os
import subprocess
import logging

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

# Function to create a video file from the combined audio and an image
def create_video(audio_file, image_file, output_file, fps=24, max_height=4096):
    audio_clip = AudioFileClip(str(audio_file))
    video_clip = ImageClip(image_file).set_duration(audio_clip.duration).set_fps(fps)
    video_clip = video_clip.set_audio(audio_clip)

    use_gpu = is_gpu_encoding_available()

    # Check if video needs scaling
    video_scaled_file = None
    try:
        video_clip = VideoFileClip(image_file)
        if video_clip.size[1] > max_height:
            logging.debug(f"Video height {video_clip.size[1]} exceeds max height {max_height}, scaling required.")
            video_scaled_file = Path(output_file).with_suffix(".scaled.mp4")
            scale_video(image_file, video_scaled_file, max_height)
            image_file = video_scaled_file
    except Exception as e:
        logging.error(f"Error checking/scaling video resolution: {e}")

    try:
        video_clip.write_videofile(
            str(output_file),
            codec='h264_nvenc' if use_gpu else 'libx264',
            audio_codec='aac',
            fps=fps,
            preset='fast'
        )
    except Exception as e:
        logging.error(f"Video encoding failed. Error: {e}")
        messagebox.showerror("Error", f"Video encoding failed. Error: {e}")
        if "No NVENC capable devices found" in str(e):
            logging.error("Ensure your NVIDIA drivers are correctly installed and your GPU supports NVENC.")
        logging.info("Falling back to CPU encoding.")
        video_clip.write_videofile(
            str(output_file),
            codec='libx264',
            audio_codec='aac',
            fps=fps,
            preset='fast'
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

# Create GUI
root = tk.Tk()
root.title("Combine MP3s and Convert to Video")

frame = tk.Frame(root, padx=10, pady=10)
frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Create the Listbox with a scrollbar
listbox_frame = tk.Frame(frame)
listbox_frame.grid(row=0, column=0, columnspan=3, sticky=tk.NSEW)

scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL)
listbox = tk.Listbox(listbox_frame, selectmode=tk.SINGLE, width=50, height=10, yscrollcommand=scrollbar.set)
scrollbar.config(command=listbox.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Configure grid to make the Listbox resizable
frame.grid_rowconfigure(0, weight=1)
frame.grid_columnconfigure(0, weight=1)

tk.Button(frame, text="Browse MP3 Files...", command=select_files).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
tk.Button(frame, text="Move Up", command=move_up).grid(row=1, column=1, padx=5, pady=5)
tk.Button(frame, text="Move Down", command=move_down).grid(row=1, column=2, padx=5, pady=5, sticky=tk.E)

tk.Label(frame, text="Select Background Image:").grid(row=2, column=0, sticky=tk.W)
image_entry = tk.Entry(frame, width=50)
image_entry.grid(row=2, column=1, padx=5, pady=5)
tk.Button(frame, text="Browse...", command=select_image).grid(row=2, column=2, padx=5, pady=5)

tk.Label(frame, text="Output Folder:").grid(row=3, column=0, sticky=tk.W)
folder_entry = tk.Entry(frame, width=50)
folder_entry.grid(row=3, column=1, padx=5, pady=5)
tk.Button(frame, text="Browse...", command=select_output_folder).grid(row=3, column=2, padx=5, pady=5)

tk.Label(frame, text="Output File Name (without extension):").grid(row=4, column=0, sticky=tk.W)
output_name_entry = tk.Entry(frame, width=50)
output_name_entry.grid(row=4, column=1, padx=5, pady=5)

tk.Button(frame, text="Start Conversion", command=start_conversion).grid(row=5, column=0, columnspan=2, pady=10)
tk.Button(frame, text="Clear Fields", command=clear_fields).grid(row=5, column=2, pady=10)

# Load the previous configuration if available
load_config()

root.mainloop()
