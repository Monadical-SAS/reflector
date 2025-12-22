"""
Shared transcript processing constants.

Used by both Hatchet workflows and Celery pipelines for consistent processing.
"""

# Topic detection: number of words per chunk for topic extraction
TOPIC_CHUNK_WORD_COUNT = 300
