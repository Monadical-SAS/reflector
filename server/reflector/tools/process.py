import av
from reflector.logger import logger
from reflector.processors import (
    Pipeline,
    AudioChunkerProcessor,
    AudioMergeProcessor,
    AudioTranscriptAutoProcessor,
    TranscriptLinerProcessor,
    TranscriptTopicDetectorProcessor,
    TranscriptFinalSummaryProcessor,
)
import asyncio


async def process_audio_file(filename, event_callback, only_transcript=False):
    async def on_transcript(data):
        await event_callback("transcript", data)

    async def on_topic(data):
        await event_callback("topic", data)

    async def on_summary(data):
        await event_callback("summary", data)

    # build pipeline for audio processing
    processors = [
        AudioChunkerProcessor(),
        AudioMergeProcessor(),
        AudioTranscriptAutoProcessor.as_threaded(),
        TranscriptLinerProcessor(callback=on_transcript),
    ]
    if not only_transcript:
        processors += [
            TranscriptTopicDetectorProcessor.as_threaded(callback=on_topic),
            TranscriptFinalSummaryProcessor.as_threaded(callback=on_summary),
        ]

    # transcription output
    pipeline = Pipeline(*processors)
    pipeline.describe()

    # start processing audio
    logger.info(f"Opening {filename}")
    container = av.open(filename)
    try:
        logger.info("Start pushing audio into the pipeline")
        for frame in container.decode(audio=0):
            await pipeline.push(frame)
    finally:
        logger.info("Flushing the pipeline")
        await pipeline.flush()

    logger.info("All done !")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Source file (mp3, wav, mp4...)")
    parser.add_argument("--only-transcript", "-t", action="store_true")
    args = parser.parse_args()

    async def event_callback(event, data):
        if event == "transcript":
            print(f"Transcript[{data.human_timestamp}]: {data.text}")
        elif event == "topic":
            print(f"Topic: {data}")
        elif event == "summary":
            print(f"Summary: {data}")

    asyncio.run(
        process_audio_file(
            args.source, event_callback, only_transcript=args.only_transcript
        )
    )
