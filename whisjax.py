#!/usr/bin/env python3

# summarize https://www.youtube.com/watch?v=imzTxoEDH_g --transcript=transcript.txt summary.txt
# summarize https://www.sprocket.org/video/cheesemaking.mp4 summary.txt
# summarize podcast.mp3 summary.txt

from urllib.parse import urlparse
from pytube import YouTube
from loguru import logger
from whisper_jax import FlaxWhisperPipline
import jax.numpy as jnp
import moviepy.editor
import argparse
import tempfile
import whisper
import openai
import re
import configparser
import os

config = configparser.ConfigParser()
config.read('config.ini')

WHISPER_MODEL_SIZE = config['DEFAULT']["WHISPER_MODEL_SIZE"]
OPENAI_APIKEY = config['DEFAULT']["OPENAI_APIKEY"]

MAX_WORDS_IN_CHUNK = 2500
MAX_OUTPUT_TOKENS = 1000


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTIONS] <LOCATION> <OUTPUT>",
        description="Creates a transcript of a video or audio file, then summarizes it using ChatGPT."
    )

    parser.add_argument("-l", "--language", help="Language that the summary should be written in", type=str,
                        default="english", choices=['english', 'spanish', 'french', 'german', 'romanian'])
    parser.add_argument("-t", "--transcript", help="Save a copy of the intermediary transcript file", type=str)
    parser.add_argument("location")
    parser.add_argument("output")

    return parser


def chunk_text(txt):
    sentences = re.split('[.!?]', txt)

    chunks = []
    chunk = ""
    size = 0

    for s in sentences:
        # Get the number of words in this sentence.
        n = len(re.findall(r'\w+', s))

        # Skip over empty sentences.
        if n == 0:
            continue

        # We need to break the text up into chunks so as not to exceed the max
        # number of tokens accepted by the ChatGPT model.
        if size + n > MAX_WORDS_IN_CHUNK:
            chunks.append(chunk)
            size = n
            chunk = s
        else:
            chunk = chunk + s
            size = size + n

    if chunk:
        chunks.append(chunk)

    return chunks


def main():
    parser = init_argparse()
    args = parser.parse_args()

    # Parse the location string that was given to us, and figure out if it's a
    # local file (audio or video), a YouTube URL, or a URL referencing an
    # audio or video file.
    url = urlparse(args.location)

    media_file = ""
    if url.scheme == 'http' or url.scheme == 'https':
        # Check if we're being asked to retreive a YouTube URL, which is handled
        # diffrently, as we'll use a secondary site to download the video first.
        if re.search('youtube.com', url.netloc, re.IGNORECASE):
            # Download the lowest resolution YouTube video (since we're just interested in the audio).
            # It will be saved to the current directory.
            logger.info("Downloading YouTube video at url: " + args.location)

            youtube = YouTube(args.location)
            media_file = youtube.streams.filter(progressive=True, file_extension='mp4').order_by(
                'resolution').asc().first().download()

            logger.info("Saved downloaded YouTube video to: " + media_file)
        else:
            # XXX - Download file using urllib, check if file is audio/video using python-magic
            logger.info(f"Downloading file at url: {args.location}")
            logger.info("  XXX - This method hasn't been implemented yet.")
    elif url.scheme == '':
        media_file = url.path
    else:
        print("Unsupported URL scheme: " + url.scheme)
        quit()

    # If the media file we just retrieved is a video, extract its audio stream.
    # XXX - We should be checking if we've downloaded an audio file (eg .mp3),
    # XXX - in which case we can skip this step.  For now we'll assume that
    # XXX - everything is an mp4 video.
    audio_filename = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
    logger.info(f"Extracting audio to: {audio_filename}")

    video = moviepy.editor.VideoFileClip(media_file)
    video.audio.write_audiofile(audio_filename, logger=None)

    logger.info("Finished extracting audio")

    # Convert the audio to text using the OpenAI Whisper model
    pipeline = FlaxWhisperPipline("openai/whisper-" + WHISPER_MODEL_SIZE, dtype=jnp.float16, batch_size=16)
    whisper_result = pipeline(audio_filename, return_timestamps=True)
    logger.info("Finished transcribing file")

    # If we got the transcript parameter on the command line, save the transcript to the specified file.
    if args.transcript:
        logger.info(f"Saving transcript to: {args.transcript}")
        transcript_file = open(args.transcript, "w")
        transcript_file.write(whisper_result["text"])
        transcript_file.close()

    # Summarize the generated transcript using OpenAI
    openai.api_key = OPENAI_APIKEY

    # Break the text up into smaller chunks for ChatGPT to summarize.
    logger.info(f"Breaking transcript up into smaller chunks with MAX_WORDS_IN_CHUNK = {MAX_WORDS_IN_CHUNK}")
    chunks = chunk_text(whisper_result['text'])
    logger.info(f"Transcript broken up into {len(chunks)} chunks")

    language = args.language

    logger.info(f"Writing summary text in {language} to: {args.output}")
    with open(args.output, 'w') as f:
        f.write('Summary of: ' + args.location + "\n\n")

        for c in chunks:
            response = openai.ChatCompletion.create(
                frequency_penalty=0.0,
                max_tokens=1000,
                model="gpt-3.5-turbo",
                presence_penalty=1.0,
                temperature=0.2,
                messages=[
                    {"role": "system",
                     "content": f"You are an assistant helping to summarize transcipts of an audio or video conversation.  The summary should be written in the {language} language."},
                    {"role": "user", "content": c}
                ],
            )
            f.write(response['choices'][0]['message']['content'] + "\n\n")

    logger.info("Summarization completed")


if __name__ == "__main__":
    # os.environ['KMP_DUPLICATE_LIB_OK'] = "1"
    print("Gokul", os.environ['KMP_DUPLICATE_LIB_OK'])
    main()
