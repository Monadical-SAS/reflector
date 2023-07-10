#!/bin/bash

# Directory to search for Python files
directory="."

# Pattern to match Python files (e.g., "*.py" for all .py files)
text_file_pattern="transcript_*.txt"
pickle_file_pattern="*.pkl"
html_file_pattern="*.html"
png_file_pattern="*.png"

find "$directory" -type f -name "$text_file_pattern" -delete
find "$directory" -type f -name "$pickle_file_pattern" -delete
find "$directory" -type f -name "$html_file_pattern" -delete
find "$directory" -type f -name "$png_file_pattern" -delete
