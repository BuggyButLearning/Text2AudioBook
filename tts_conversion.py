import logging
import requests
from pathlib import Path
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor

def convert_text_chunk_to_speech(chunk, index, api_key, voice, output_folder, timestamp):
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.post('https://api.openai.com/v1/audio/speech',
                             json={'model': 'tts-1', 'input': chunk, 'voice': voice},
                             headers=headers)
    if response.status_code == 200:
        file_path = output_folder / f"chunk_part_{index + 1}_{timestamp}.mp3"
        with open(file_path, 'wb') as file:
            file.write(response.content)
        logging.info(f"Chunk {index + 1} converted to speech and saved to {file_path}.")
        return file_path
    else:
        logging.error(f"Failed to convert chunk {index + 1} to speech: {response.text}")
        return None

def convert_text_to_speech(text_chunks, api_key, voice, output_folder, timestamp):
    audio_files = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(convert_text_chunk_to_speech, chunk, i, api_key, voice, output_folder, timestamp) for i, chunk in enumerate(text_chunks)]
        for future in futures:
            result = future.result()
            if result:
                audio_files.append(result)
    return audio_files

def concatenate_audio_files(audio_files, output_file_path):
    combined = AudioSegment.empty()
    for file_path in audio_files:
        sound = AudioSegment.from_mp3(file_path)
        combined += sound
    combined.export(output_file_path, format="mp3")
    logging.info(f"All chunks concatenated into {output_file_path}")
