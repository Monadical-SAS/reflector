import argparse
import os
import tempfile

import moviepy.editor
import nltk
import whisper
from loguru import logger
from transformers import BartTokenizer, BartForConditionalGeneration

nltk.download('punkt', quiet=True)

WHISPER_MODEL_SIZE = "base"


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTIONS] <LOCATION> <OUTPUT>",
        description="Creates a transcript of a video or audio file, then summarizes it using BART."
    )

    parser.add_argument("location", help="Location of the media file")
    parser.add_argument("output", help="Output file path")

    parser.add_argument(
        "-t", "--transcript", help="Save a copy of the intermediary transcript file", type=str)
    parser.add_argument(
        "-l", "--language", help="Language that the summary should be written in",
        type=str, default="english", choices=['english', 'spanish', 'french', 'german', 'romanian'])
    parser.add_argument(
        "-m", "--model_name", help="Name or path of the BART model",
        type=str, default="facebook/bart-large-cnn")

    return parser


# NLTK chunking function
def chunk_text(txt, max_chunk_length=500):
    "Split text into smaller chunks."
    sentences = nltk.sent_tokenize(txt)
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_chunk_length:
            current_chunk += f" {sentence.strip()}"
        else:
            chunks.append(current_chunk.strip())
            current_chunk = f"{sentence.strip()}"
    chunks.append(current_chunk.strip())
    return chunks


# BART summary function
def summarize_chunks(chunks, tokenizer, model):
    summaries = []
    for c in chunks:
        input_ids = tokenizer.encode(c, return_tensors='pt')
        summary_ids = model.generate(
            input_ids, num_beams=4, length_penalty=2.0, max_length=1024, no_repeat_ngram_size=3)
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        summaries.append(summary)
    return summaries


def main():
    import sys
    sys.setrecursionlimit(10000)

    parser = init_argparse()
    args = parser.parse_args()

    media_file = args.location
    logger.info(f"Processing file: {media_file}")

    # If the media file we just retrieved is a video, extract its audio stream.
    if os.path.isfile(media_file) and media_file.endswith(('.mp4', '.avi', '.flv')):
        audio_filename = tempfile.NamedTemporaryFile(
            suffix=".mp3", delete=False).name
        logger.info(f"Extracting audio to: {audio_filename}")

        video = moviepy.editor.VideoFileClip(media_file)
        video.audio.write_audiofile(audio_filename, logger=None)

        logger.info("Finished extracting audio")
        media_file = audio_filename

    # Transcribe the audio file using the OpenAI Whisper model
    logger.info("Loading Whisper speech-to-text model")
    whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)

    logger.info(f"Transcribing audio file: {media_file}")
    whisper_result = whisper_model.transcribe(media_file)

    logger.info("Finished transcribing file")

    # If we got the transcript parameter on the command line, save the transcript to the specified file.
    if args.transcript:
        logger.info(f"Saving transcript to: {args.transcript}")
        transcript_file = open(args.transcript, "w")
        transcript_file.write(whisper_result["text"])
        transcript_file.close()

    # Summarize the generated transcript using the BART model
    logger.info(f"Loading BART model: {args.model_name}")
    tokenizer = BartTokenizer.from_pretrained(args.model_name)
    model = BartForConditionalGeneration.from_pretrained(args.model_name)

    logger.info("Breaking transcript into smaller chunks")
    chunks = chunk_text(whisper_result['text'])

    logger.info(
        f"Transcript broken into {len(chunks)} chunks of at most 500 words")  # TODO fix variable

    logger.info(f"Writing summary text in {args.language} to: {args.output}")
    with open(args.output, 'w') as f:
        f.write('Summary of: ' + args.location + "\n\n")
        summaries = summarize_chunks(chunks, tokenizer, model)
        for summary in summaries:
            f.write(summary.strip() + "\n\n")

    logger.info("Summarization completed")


if __name__ == "__main__":
    main()
