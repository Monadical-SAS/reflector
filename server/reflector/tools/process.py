import asyncio

import av
from reflector.logger import logger
from reflector.processors import (
    AudioChunkerProcessor,
    AudioMergeProcessor,
    AudioTranscriptAutoProcessor,
    Pipeline,
    PipelineEvent,
    TranscriptFinalSummaryProcessor,
    TranscriptFinalTitleProcessor,
    TranscriptLinerProcessor,
    TranscriptTopicDetectorProcessor,
    TranscriptTranslatorProcessor,
)
from reflector.processors.base import BroadcastProcessor


async def process_audio_file(
    filename,
    event_callback,
    only_transcript=False,
    source_language="en",
    target_language="en",
):
    # build pipeline for audio processing
    processors = [
        AudioChunkerProcessor(),
        AudioMergeProcessor(),
        AudioTranscriptAutoProcessor.as_threaded(),
        TranscriptLinerProcessor(),
        TranscriptTranslatorProcessor.as_threaded(),
    ]
    if not only_transcript:
        processors += [
            TranscriptTopicDetectorProcessor.as_threaded(),
            BroadcastProcessor(
                processors=[
                    TranscriptFinalTitleProcessor.as_threaded(),
                    TranscriptFinalSummaryProcessor.as_threaded(),
                ],
            ),
        ]

    # transcription output
    pipeline = Pipeline(*processors)
    pipeline.set_pref("audio:source_language", source_language)
    pipeline.set_pref("audio:target_language", target_language)
    pipeline.describe()
    pipeline.on(event_callback)

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
    parser.add_argument("--source-language", default="en")
    parser.add_argument("--target-language", default="en")
    parser.add_argument("--output", "-o", help="Output file (output.jsonl)")
    args = parser.parse_args()

    output_fd = None
    if args.output:
        output_fd = open(args.output, "w")

    async def event_callback(event: PipelineEvent):
        processor = event.processor
        # ignore some processor
        if processor in ("AudioChunkerProcessor", "AudioMergeProcessor"):
            return
        logger.info(f"Event: {event}")
        if output_fd:
            output_fd.write(event.model_dump_json())
            output_fd.write("\n")

    asyncio.run(
        process_audio_file(
            args.source,
            event_callback,
            only_transcript=args.only_transcript,
            source_language=args.source_language,
            target_language=args.target_language,
        )
    )

    if output_fd:
        output_fd.close()
        logger.info(f"Output written to {args.output}")
