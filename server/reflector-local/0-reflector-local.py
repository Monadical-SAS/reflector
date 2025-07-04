import os
import subprocess
import sys

from loguru import logger

# Get the input file name from the command line argument
input_file = sys.argv[1]
# example use: python 0-reflector-local.py input.m4a agenda.txt

# Get the agenda file name from the command line argument if provided
if len(sys.argv) > 2:
    agenda_file = sys.argv[2]
else:
    agenda_file = "agenda.txt"
# example use: python 0-reflector-local.py input.m4a my_agenda.txt

# Check if the agenda file exists
if not os.path.exists(agenda_file):
    logger.error("agenda_file is missing")

# Check if the input file is .m4a, if so convert to .mp4
if input_file.endswith(".m4a"):
    subprocess.run(["ffmpeg", "-i", input_file, f"{input_file}.mp4"])
    input_file = f"{input_file}.mp4"

# Run the first script to generate the transcript
subprocess.run(
    ["python3", "1-transcript-generator.py", input_file, f"{input_file}_transcript.txt"]
)

# Run the second script to compare the transcript to the agenda
subprocess.run(
    [
        "python3",
        "2-agenda-transcript-diff.py",
        agenda_file,
        f"{input_file}_transcript.txt",
    ]
)

# Run the third script to summarize the transcript
subprocess.run(
    [
        "python3",
        "3-transcript-summarizer.py",
        f"{input_file}_transcript.txt",
        f"{input_file}_summary.txt",
    ]
)
