import argparse
import asyncio

from reflector.pipelines.main_live_pipeline import pipeline_post

parser = argparse.ArgumentParser()
parser.add_argument("transcript_id", type=str)
args = parser.parse_args()

asyncio.run(pipeline_post(transcript_id=args.transcript_id))
