import argparse

from reflector.app import celery_app  # noqa
from reflector.pipelines.main_live_pipeline import task_pipeline_main_post

parser = argparse.ArgumentParser()
parser.add_argument("transcript_id", type=str)
parser.add_argument("--delay", action="store_true")
args = parser.parse_args()

if args.delay:
    task_pipeline_main_post.delay(args.transcript_id)
else:
    task_pipeline_main_post(args.transcript_id)
