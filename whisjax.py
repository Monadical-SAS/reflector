#!/usr/bin/env python3

# summarize https://www.youtube.com/watch?v=imzTxoEDH_g --transcript=transcript.txt summary.txt
# summarize https://www.sprocket.org/video/cheesemaking.mp4 summary.txt
# summarize podcast.mp3 summary.txt

import argparse
import configparser
import jax.numpy as jnp

import moviepy.editor
import moviepy.editor
import nltk
import os
import subprocess
import re
import tempfile
from loguru import logger
import yt_dlp as youtube_dl

from urllib.parse import urlparse
from whisper_jax import FlaxWhisperPipline

from datetime import datetime
from reflector.utils.file_utilities import upload_files, download_files
from reflector.utils.viz_utilities import create_wordcloud, create_talk_diff_scatter_viz
from reflector.utils.text_utilities import summarize, post_process_transcription

nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

# Configurations can be found in config.ini. Set them properly before executing
config = configparser.ConfigParser()
config.read('config.ini')

WHISPER_MODEL_SIZE = config['DEFAULT']["WHISPER_MODEL_SIZE"]
NOW = datetime.now()

def init_argparse() -> argparse.ArgumentParser:
    """
    Parse the CLI arguments
    :return: parser object
    """
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTIONS] <LOCATION> <OUTPUT>",
        description="Creates a transcript of a video or audio file, then summarizes it using ChatGPT."
    )

    parser.add_argument("-l", "--language", help="Language that the summary should be written in", type=str,
                        default="english", choices=['english', 'spanish', 'french', 'german', 'romanian'])
    parser.add_argument("location")
    return parser



def main():
    parser = init_argparse()
    args = parser.parse_args()

    # Parse the location string that was given to us, and figure out if it's a
    # local file (audio or video), a YouTube URL, or a URL referencing an
    # audio or video file.
    url = urlparse(args.location)

    # S3 : Pull artefacts to S3 bucket ?

    media_file = ""
    if url.scheme == 'http' or url.scheme == 'https':
        # Check if we're being asked to retreive a YouTube URL, which is handled
        # diffrently, as we'll use a secondary site to download the video first.
        if re.search('youtube.com', url.netloc, re.IGNORECASE):
            # Download the lowest resolution YouTube video (since we're just interested in the audio).
            # It will be saved to the current directory.
            logger.info("Downloading YouTube video at url: " + args.location)

            # Create options for the download
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': 'audio',  # Specify the output file path and name
            }

            # Download the audio
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([args.location])
            media_file = "audio.mp3"

            logger.info("Saved downloaded YouTube video to: " + media_file)
        else:
            # XXX - Download file using urllib, check if file is audio/video using python-magic
            logger.info(f"Downloading file at url: {args.location}")
            logger.info("  XXX - This method hasn't been implemented yet.")
    elif url.scheme == '':
        media_file = url.path
        # If file is not present locally, take it from S3 bucket
        if not os.path.exists(media_file):
            download_files([media_file])

        if media_file.endswith(".m4a"):
            subprocess.run(["ffmpeg", "-i", media_file, f"{media_file}.mp4"])
            input_file = f"{media_file}.mp4"
    else:
        print("Unsupported URL scheme: " + url.scheme)
        quit()

    # Handle video
    if not media_file.endswith(".mp3"):
        try:
            video = moviepy.editor.VideoFileClip(media_file)
            audio_filename = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
            video.audio.write_audiofile(audio_filename, logger=None)
            logger.info(f"Extracting audio to: {audio_filename}")
        # Handle audio only file
        except:
            audio = moviepy.editor.AudioFileClip(media_file)
            audio_filename = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
            audio.write_audiofile(audio_filename, logger=None)
    else:
        audio_filename = media_file

    logger.info("Finished extracting audio")

    # Convert the audio to text using the OpenAI Whisper model
    pipeline = FlaxWhisperPipline("openai/whisper-" + WHISPER_MODEL_SIZE,
                                  dtype=jnp.float16,
                                  batch_size=16)
    whisper_result = pipeline(audio_filename, return_timestamps=True)
    logger.info("Finished transcribing file")

    whisper_result = post_process_transcription(whisper_result)

    transcript_text = ""
    for chunk in whisper_result["chunks"]:
        transcript_text += chunk["text"]

    with open("transcript_" + NOW.strftime("%m-%d-%Y_%H:%M:%S") + ".txt", "w") as transcript_file:
        transcript_file.write(transcript_text)

    with open("transcript_with_timestamp_" + NOW.strftime("%m-%d-%Y_%H:%M:%S") + ".txt", "w") as transcript_file_timestamps:
        transcript_file_timestamps.write(str(whisper_result))


    logger.info("Creating word cloud")
    create_wordcloud(NOW)

    logger.info("Performing talk-diff and talk-diff visualization")
    create_talk_diff_scatter_viz(NOW)

    # S3 : Push artefacts to S3 bucket
    suffix = NOW.strftime("%m-%d-%Y_%H:%M:%S")
    files_to_upload = ["transcript_" + suffix + ".txt",
                       "transcript_with_timestamp_" + suffix + ".txt",
                       "df_" + suffix + ".pkl",
                       "wordcloud_" + suffix + ".png",
                       "mappings_" + suffix + ".pkl",
                       "scatter_" + suffix + ".html"]
    upload_files(files_to_upload)

    summarize(transcript_text, NOW, False, False)

    logger.info("Summarization completed")

    # Summarization takes a lot of time, so do this separately at the end
    files_to_upload = ["summary_" + suffix + ".txt"]
    upload_files(files_to_upload)


if __name__ == "__main__":
    main()
