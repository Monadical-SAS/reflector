"""
# Run a pipeline of processor

This tools help to either create a pipeline from command line,
or read a yaml description of a pipeline and run it.
"""

import json

from reflector.logger import logger
from reflector.processors import Pipeline, PipelineEvent


def camel_to_snake(s):
    return "".join(["_" + c.lower() if c.isupper() else c for c in s]).lstrip("_")


def snake_to_camel(s):
    return "".join([c.capitalize() for c in s.split("_")])


def get_jsonl(filename, filter_processor_name=None):
    logger.info(f"Opening {args.input}")
    if filter_processor_name is not None:
        filter_processor_name = snake_to_camel(filter_processor_name) + "Processor"
        logger.info(f"Filtering on {filter_processor_name}")

    with open(filename, encoding="utf8") as f:
        for line in f:
            data = json.loads(line)
            if (
                filter_processor_name is not None
                and data["processor"] != filter_processor_name
            ):
                continue
            yield data


def get_processor(name):
    import importlib

    module_name = f"reflector.processors.{name}"
    class_name = snake_to_camel(name) + "Processor"
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


async def run_single_processor(args):
    output_fd = None
    if args.output:
        output_fd = open(args.output, "w")

    async def event_callback(event: PipelineEvent):
        processor = event.processor
        # ignore some processor
        if processor in ("AudioChunkerProcessor", "AudioMergeProcessor"):
            return
        print(f"Event: {event}")
        if output_fd:
            output_fd.write(event.model_dump_json())
            output_fd.write("\n")

    processor = get_processor(args.processor)()
    pipeline = Pipeline(processor)
    pipeline.on(event_callback)
    input_type = pipeline.INPUT_TYPE

    logger.info(f"Converting to {input_type.__name__} type")

    for data in get_jsonl(args.input, filter_processor_name=args.input_processor):
        obj = input_type(**data["data"])
        await pipeline.push(obj)
    await pipeline.flush()

    if output_fd:
        output_fd.close()
        logger.info(f"Output written to {args.output}")


if __name__ == "__main__":
    import argparse
    import asyncio
    import sys

    parser = argparse.ArgumentParser(description="Run a pipeline of processor")
    parser.add_argument("--input", "-i", help="Input file (jsonl)")
    parser.add_argument("--input-processor", "-f", help="Name of the processor to keep")
    parser.add_argument("--output", "-o", help="Output file (jsonl)")
    parser.add_argument("--pipeline", "-p", help="Pipeline description (yaml)")
    parser.add_argument("--processor", help="Processor to run")
    args = parser.parse_args()

    if args.output and args.output == args.input:
        parser.error("Input and output cannot be the same")
        sys.exit(1)

    if args.processor and args.pipeline:
        parser.error("--processor and --pipeline are mutually exclusive")
        sys.exit(1)

    if not args.processor and not args.pipeline:
        parser.error("You need to specify either --processor or --pipeline")
        sys.exit(1)

    if args.processor:
        func = run_single_processor(args)
    # elif args.pipeline:
    #     func = run_pipeline(args)

    asyncio.run(func)
