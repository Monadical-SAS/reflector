#!/usr/bin/env python3

import configparser
import pyaudio
from whisper_jax import FlaxWhisperPipline
from pynput import keyboard
import jax.numpy as jnp
import wave
from datetime import datetime
from reflector.utils.file_utilities import upload_files
from reflector.utils.viz_utilities import create_wordcloud, create_talk_diff_scatter_viz
from reflector.utils.text_utilities import summarize, post_process_transcription
from loguru import logger
import time
from termcolor import colored

config = configparser.ConfigParser()
config.read('config.ini')

WHISPER_MODEL_SIZE = config['DEFAULT']["WHISPER_MODEL_SIZE"]

FRAMES_PER_BUFFER = 8000
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 96000
RECORD_SECONDS = 15
NOW = datetime.now()


def main():
    p = pyaudio.PyAudio()
    AUDIO_DEVICE_ID = -1
    for i in range(p.get_device_count()):
        if p.get_device_info_by_index(i)["name"] == config["DEFAULT"]["BLACKHOLE_INPUT_AGGREGATOR_DEVICE_NAME"]:
            AUDIO_DEVICE_ID = i
    audio_devices = p.get_device_info_by_index(AUDIO_DEVICE_ID)
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=FRAMES_PER_BUFFER,
        input_device_index=int(audio_devices['index'])
    )

    pipeline = FlaxWhisperPipline("openai/whisper-" + config["DEFAULT"]["WHISPER_REAL_TIME_MODEL_SIZE"],
                                  dtype=jnp.float16,
                                  batch_size=16)

    transcription = ""

    TEMP_AUDIO_FILE = "temp_audio.wav"
    global proceed
    proceed = True

    def on_press(key):
        if key == keyboard.Key.esc:
            global proceed
            proceed = False

    transcript_with_timestamp = {"text": "", "chunks": []}
    last_transcribed_time = 0.0

    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    print("Attempting real-time transcription.. Listening...")

    try:
        while proceed:
            frames = []
            start_time = time.time()
            for i in range(0, int(RATE / FRAMES_PER_BUFFER * RECORD_SECONDS)):
                data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                frames.append(data)
            end_time = time.time()

            wf = wave.open(TEMP_AUDIO_FILE, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()

            whisper_result = pipeline(TEMP_AUDIO_FILE, return_timestamps=True)
            timestamp = whisper_result["chunks"][0]["timestamp"]
            start = timestamp[0]
            end = timestamp[1]
            if end is None:
                end = start + 15.0
            duration = end - start
            item = {'timestamp': (last_transcribed_time, last_transcribed_time + duration),
                    'text': whisper_result['text'],
                    'stats': (str(end_time - start_time), str(duration))
                    }
            last_transcribed_time = last_transcribed_time + duration
            transcript_with_timestamp["chunks"].append(item)
            transcription += whisper_result['text']

            print(colored("<START>", "yellow"))
            print(colored(whisper_result['text'], 'green'))
            print(colored("<END> Recorded duration: " + str(end_time - start_time) + " | Transcribed duration: " +
                          str(duration), "yellow"))

    except Exception as e:
        print(e)
    finally:
        with open("real_time_transcript_" + NOW.strftime("%m-%d-%Y_%H:%M:%S") + ".txt", "w") as f:
            f.write(transcription)
        with open("real_time_transcript_with_timestamp_" + NOW.strftime("%m-%d-%Y_%H:%M:%S") + ".txt", "w") as f:
            transcript_with_timestamp["text"] = transcription
            f.write(str(transcript_with_timestamp))

    transcript_with_timestamp = post_process_transcription(transcript_with_timestamp)

    logger.info("Creating word cloud")
    create_wordcloud(NOW, True)

    logger.info("Performing talk-diff and talk-diff visualization")
    create_talk_diff_scatter_viz(NOW, True)

    # S3 : Push artefacts to S3 bucket
    suffix = NOW.strftime("%m-%d-%Y_%H:%M:%S")
    files_to_upload = ["real_time_transcript_" + suffix + ".txt",
                       "real_time_transcript_with_timestamp_" + suffix + ".txt",
                       "real_time_df_" + suffix + ".pkl",
                       "real_time_wordcloud_" + suffix + ".png",
                       "real_time_mappings_" + suffix + ".pkl",
                       "real_time_scatter_" + suffix + ".html"]
    upload_files(files_to_upload)

    summarize(transcript_with_timestamp["text"], NOW, True, True)

    logger.info("Summarization completed")

    # Summarization takes a lot of time, so do this separately at the end
    files_to_upload = ["real_time_summary_" + suffix + ".txt"]
    upload_files(files_to_upload)


if __name__ == "__main__":
    main()
