#!/usr/bin/env python3

import configparser
import pyaudio
from whisper_jax import FlaxWhisperPipline
from pynput import keyboard
import jax.numpy as jnp
import wave

config = configparser.ConfigParser()
config.read('config.ini')

WHISPER_MODEL_SIZE = config['DEFAULT']["WHISPER_MODEL_SIZE"]

FRAMES_PER_BUFFER = 8000
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 15


def main():
    p = pyaudio.PyAudio()
    AUDIO_DEVICE_ID = -1
    for i in range(p.get_device_count()):
        if p.get_device_info_by_index(i)["name"] == "ref-agg-input":
            AUDIO_DEVICE_ID = i
    audio_devices = p.get_device_info_by_index(AUDIO_DEVICE_ID)
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=FRAMES_PER_BUFFER,
        input_device_index=audio_devices['index']
    )

    pipeline = FlaxWhisperPipline("openai/whisper-" + config["DEFAULT"]["WHISPER_REAL_TIME_MODEL_SIZE"],
                                  dtype=jnp.float16,
                                  batch_size=16)

    transcript_file = open("transcript.txt", "w+")
    transcription = ""

    TEMP_AUDIO_FILE = "temp_audio.wav"
    global proceed
    proceed = True

    def on_press(key):
        if key == keyboard.Key.esc:
            global proceed
            proceed = False

    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    print("Attempting real-time transcription.. Listening...")
    while proceed:
        try:
            frames = []
            for i in range(0, int(RATE / FRAMES_PER_BUFFER * RECORD_SECONDS)):
                data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                frames.append(data)

            wf = wave.open(TEMP_AUDIO_FILE, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()

            whisper_result = pipeline(TEMP_AUDIO_FILE, return_timestamps=True)
            print(whisper_result['text'])

            transcription += whisper_result['text']

        except Exception as e:
            print(e)
        finally:
            with open("real_time_transcription.txt", "w") as f:
                transcript_file.write(transcription)


if __name__ == "__main__":
    main()
