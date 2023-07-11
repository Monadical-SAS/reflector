import argparse
import os

import moviepy.editor
import whisper
from loguru import logger

WHISPER_MODEL_SIZE = "base"


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s <LOCATION> <OUTPUT>",
        description="Creates a transcript of a video or audio file using the OpenAI Whisper model"
    )
    parser.add_argument("location", help="Location of the media file")
    parser.add_argument("output", help="Output file path")
    return parser


def main():
    import sys
    sys.setrecursionlimit(10000)

    parser = init_argparse()
    args = parser.parse_args()

    media_file = args.location
    logger.info(f"Processing file: {media_file}")

    # Check if the media file is a valid audio or video file
    if os.path.isfile(media_file) and not media_file.endswith(
            ('.mp3', '.wav', '.ogg', '.flac', '.mp4', '.avi', '.flv')):
        logger.error(f"Invalid file format: {media_file}")
        return

    # If the media file we just retrieved is an audio file then skip extraction step
    audio_filename = media_file
    logger.info(f"Found audio-only file, skipping audio extraction")

    audio = moviepy.editor.AudioFileClip(audio_filename)

    logger.info("Selected extracted audio")

    # Transcribe the audio file using the OpenAI Whisper model
    logger.info("Loading Whisper speech-to-text model")
    whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)

    logger.info(f"Transcribing file: {media_file}")
    whisper_result = whisper_model.transcribe(media_file)

    logger.info("Finished transcribing file")

    # Save the transcript to the specified file.
    logger.info(f"Saving transcript to: {args.output}")
    transcript_file = open(args.output, "w")
    transcript_file.write(whisper_result["text"])
    transcript_file.close()


if __name__ == "__main__":
    main()
