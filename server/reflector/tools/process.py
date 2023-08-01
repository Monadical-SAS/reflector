from pathlib import Path
import av
from reflector.logger import logger
from reflector.processors import (
    Pipeline,
    AudioChunkerProcessor,
    AudioMergeProcessor,
    AudioTranscriptAutoProcessor,
    TranscriptLinerProcessor,
    TranscriptTopicDetectorProcessor,
    TranscriptSummarizerProcessor,
)
import asyncio


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Source file (mp3, wav, mp4...)")
    args = parser.parse_args()

    async def main():
        async def on_transcript(transcript):
            print(f"Transcript: [{transcript.human_timestamp}]: {transcript.text}")

        async def on_summary(summary):
            print(f"Summary: {summary.title} - {summary.summary}")

        async def on_final_summary(path):
            print(f"Final Summary: {path}")

        # transcription output
        result_fn = Path(args.source).with_suffix(".jsonl")

        pipeline = Pipeline(
            AudioChunkerProcessor(),
            AudioMergeProcessor(),
            AudioTranscriptAutoProcessor.as_threaded(),
            TranscriptLinerProcessor(callback=on_transcript),
            TranscriptTopicDetectorProcessor.as_threaded(callback=on_summary),
            TranscriptSummarizerProcessor.as_threaded(
                filename=result_fn, callback=on_final_summary
            ),
        )
        pipeline.describe()

        # start processing audio
        logger.info(f"Opening {args.source}")
        container = av.open(args.source)
        try:
            logger.info("Start pushing audio into the pipeline")
            for frame in container.decode(audio=0):
                await pipeline.push(frame)
        finally:
            logger.info("Flushing the pipeline")
            await pipeline.flush()

        logger.info("All done !")

    asyncio.run(main())
