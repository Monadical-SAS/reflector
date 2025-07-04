import json
import yt_dlp as youtube_dl
from whisper_jax import FlaxWhisperPipline
import jax.numpy as jnp


# Function to extract chapter information from a YouTube video URL
def get_youtube_chapters(video_id):
    video_url = "https://www.youtube.com/watch?v=" + video_id
    ydl_opts = {
        "extract_flat": "in_playlist",
        "skip_download": True,
        "quiet": True,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        video_info = ydl.extract_info(video_url, download=False)

    chapters = []

    if "chapters" in video_info:
        for chapter in video_info["chapters"]:
            start_time = chapter["start_time"]
            end_time = chapter["end_time"]
            title = chapter["title"]

            chapters.append({"start": start_time, "end": end_time, "title": title})

    return chapters


# Function to extract video transcription using yt_dlp
def get_youtube_transcription(video_id):
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": "./artefacts/audio",  # Specify output file path and name
    }

    # Download the audio
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download(["https://www.youtube.com/watch?v=" + video_id])
    media_file = "./artefacts/audio.mp3"

    pipeline = FlaxWhisperPipline(
        "openai/whisper-" + "tiny", dtype=jnp.float16, batch_size=16
    )
    whisper_result = pipeline(media_file, return_timestamps=True)
    return whisper_result["chunks"]


# Function to scrape YouTube video transcripts and chapter information
def scrape_youtube_data(video_id):
    transcript_text = get_youtube_transcription(video_id)
    chapters = get_youtube_chapters(video_id)
    print("transcript_text", transcript_text)
    print("chapters", chapters)
    return transcript_text, chapters


# Function to generate fine-tuning dataset from YouTube data
def generate_finetuning_dataset(video_ids):
    prompt_completion_pairs = []
    for video_id in video_ids:
        transcript_text, chapters = scrape_youtube_data(video_id)
        if transcript_text is not None and chapters is not None:
            for chapter in chapters:
                start_time = chapter["start"]
                end_time = chapter["end"]
                chapter_text = chapter["title"]

                prompt = ""
                for transcript in transcript_text:
                    if (
                        transcript["timestamp"][0] >= start_time
                        and transcript["timestamp"][1] < end_time
                    ):
                        prompt += transcript["text"]

                if prompt is not None:
                    completion = chapter_text
                    prompt_completion_pairs.append(
                        {"prompt": prompt, "completion": completion}
                    )

    return prompt_completion_pairs


# Add all the video ids here, the videos must have captions [chapters]
video_ids = ["yTnSEZIwnkU"]
dataset = generate_finetuning_dataset(video_ids)

with open("finetuning_dataset.jsonl", "w", encoding="utf-8") as file:
    for example in dataset:
        file.write(json.dumps(example) + "\n")
