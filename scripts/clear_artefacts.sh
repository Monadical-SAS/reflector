#!/bin/bash

# Directory to search for Python files
cwd=$(pwd)
last_component="${cwd##*/}"

if [ "$last_component" = "reflector" ]; then
    directory="./artefacts"
elif [ "$last_component" = "scripts" ]; then
    directory="../artefacts"
fi

# Pattern to match Python files (e.g., "*.py" for all .py files)
transcript_file_pattern="transcript_*.txt"
summary_file_pattern="summary_*.txt"
pickle_file_pattern="*.pkl"
html_file_pattern="*.html"
png_file_pattern="wordcloud*.png"

find "$directory" -type f -name "$transcript_file_pattern" -delete
find "$directory" -type f -name "$summary_file_pattern" -delete
find "$directory" -type f -name "$pickle_file_pattern" -delete
find "$directory" -type f -name "$html_file_pattern" -delete
find "$directory" -type f -name "$png_file_pattern" -delete
