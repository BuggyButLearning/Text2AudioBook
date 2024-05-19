
# Text2AudioBook
![Text2AudioBook](https://github.com/BuggyButLearning/Text2AudioBook/assets/162375864/7bc5c288-308f-459f-957c-04f97da146bb)

## Project Summary

This project is a GUI-based application designed to convert text files into speech using OpenAI's text-to-speech (TTS) API. It is developed in Python and utilizes the Tkinter library for its graphical user interface. The primary goal of the application is to provide a user-friendly way to transform written text into spoken audio, making content more accessible and versatile.

## Features

- **Text to Speech Conversion**: Converts text files to speech using the OpenAI API.
- **Voice Selection**: Allows users to choose from different voices for the TTS conversion.
- **Text Chunking**: Splits large text files into manageable chunks to ensure smooth processing and conversion.
- **Logging**: Logs the positions of text chunks and the sentences where each chunk starts.
- **Output Management**: Saves output audio files and chunk position logs to a specified directory.

## Components

### `main.py`
- **Purpose**: Serves as the main entry point of the application. Manages the GUI, user inputs, and initiates the text-to-speech conversion process.
- **Functions**:
  - `read_api_key(file_path)`: Reads the OpenAI API key from a file.
  - `select_file()`: Opens a file dialog for selecting a text file.
  - `select_output_folder()`: Opens a directory dialog for selecting the output folder.
  - `start_conversion()`: Handles the text-to-speech conversion process, including reading text, splitting it into chunks, converting to speech, and saving outputs.
- **GUI Elements**: Includes fields for input file selection, output folder selection, output filename, and voice selection. Also includes buttons to browse files and start the conversion.
- **Logging**: Configures logging for tracking events and errors.
- **Default Output Folder**: Uses a default output folder named `output` if no output folder is specified by the user.

### `text_processing.py`
- **Purpose**: Handles text processing tasks, including reading text from files and splitting text into chunks.
- **Functions**:
  - `read_text_from_file(file_path)`: Reads the text content from a specified file.
  - `split_text(text, max_length=3500)`: Splits the text into smaller chunks of up to 3500 characters, ensuring logical sentence breaks to avoid cutting sentences awkwardly.

### `tts_conversion.py`
- **Purpose**: Manages the conversion of text chunks to speech and the concatenation of audio files.
- **Functions**:
  - `convert_text_chunk_to_speech(chunk, index, api_key, voice, output_folder, timestamp)`: Converts a text chunk into speech using the OpenAI API and saves it as an MP3 file in the specified output folder.
  - `convert_text_to_speech(text_chunks, api_key, voice, output_folder, timestamp)`: Converts multiple text chunks to speech in parallel using a thread pool and returns a list of audio file paths.
  - `concatenate_audio_files(audio_files, output_file_path)`: Combines multiple MP3 files into a single MP3 file.

### `requirements.txt`
- **Purpose**: Lists the necessary Python libraries required for the project.
- **Dependencies**:
  - `requests`
  - `pydub`
  - `openai`
  - `moviepy`

### `install_ffmpeg.py`
- **Purpose**: Provides a script to automate the installation of FFmpeg, which is required for audio processing by pydub.
- **Function**:
  - `install_ffmpeg()`: Checks the operating system and installs FFmpeg accordingly. On Windows, it downloads and extracts FFmpeg, and updates the system PATH.

## Goals

- **Accessibility**: Transform written text into spoken audio to make content more accessible.
- **User-Friendly Interface**: Provide a simple and intuitive GUI for users to perform text-to-speech conversion without needing to write code.
- **Flexibility**: Allow users to select different voices and manage large text files by splitting them into chunks.
- **Logging and Output Management**: Log chunk positions and starting sentences to help users understand how their text is processed. Save outputs to user-specified or default directories.

## Installation and Setup

### Step 1: Install Python Dependencies

Install the required Python libraries using pip:

```sh
pip install -r requirements.txt
```

### Step 2: Install FFmpeg

FFmpeg is required for audio processing. Follow the instructions below to install it.

**Windows**
1. Download the latest FFmpeg build from the [FFmpeg Builds Repository](https://ffmpeg.org/download.html).
2. Extract the downloaded zip file.
3. Add the `bin` directory from the extracted folder to your system's PATH. This allows FFmpeg to be accessible from any command line.

**macOS**
Use Homebrew to install FFmpeg:

```sh
brew install ffmpeg
```

**Linux**
Use your package manager to install FFmpeg:

```sh
sudo apt update
sudo apt install ffmpeg
```

### Step 3: Running the Application

Run the main application:

```sh
python main.py
```

## Usage

### Preparing Your Files

1. **Save Your OpenAI API Key**:
    - Ensure your OpenAI API key is saved in a file named `key.txt` within the project directory. This key is necessary for accessing the OpenAI API services.

2. **Prepare Your Text File**:
    - Save the text you want to convert into a file named `input.txt` in the project directory. This file will be used as the input for the text-to-speech conversion.

### Running the Application

1. **Launch the Application**:
    - Run the main application by executing the following command in your terminal or command prompt:
    ```sh
    python main.py
    ```

2. **Select a Text File**:
    - In the application GUI, click the "Browse..." button next to the "Input Text File" field.
    - Navigate to and select the `input.txt` file or any other text file you want to convert.

3. **Choose an Output Folder**:
    - Click the "Browse..." button next to the "Output Folder" field.
    - Select the folder where you want to save the generated audio files and chunk positions file.
    - If you do not select an output folder, the application will use the default `output` folder in the project directory.

4. **Enter the Desired Output File Name**:
    - In the "Output File Name (without extension)" field, enter the desired name for your output file. Do not include any file extension (e.g., enter `audiobook`, not `audiobook.mp3`).

5. **Select a Voice**:
    - From the "Select Voice" dropdown menu, choose the voice you want to use for the text-to-speech conversion. Options include various synthetic voices provided by OpenAI.

6. **Start the Conversion**:
    - Click the "Start Conversion" button to begin the text-to-speech conversion process.
    - The application will process the text file, convert it to speech, and save the output audio file and chunk positions file in the specified output folder.
    - A message box will inform you when the conversion is complete and provide the location of the saved files.

## Troubleshooting

- If you encounter issues with FFmpeg installation, ensure the `bin` directory is correctly added to your system's PATH.
- For Python dependency issues, verify that you are using the correct version of Python (3.7 or higher).

## Contributing

We welcome contributions! Please fork the repository and create a pull request with your changes. Ensure your code adheres to the project's coding standards and includes appropriate tests.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
