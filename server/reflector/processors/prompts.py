"""
LLM prompts for transcript processing.

Extracted to a separate module to avoid circular imports when importing
from processor modules (which import LLM/settings at module level).
"""

from textwrap import dedent

TOPIC_PROMPT = dedent(
    """
    Analyze the following transcript segment and extract the main topic being discussed.
    Focus on the substantive content and ignore small talk or administrative chatter.

    Create a title that:
    - Captures the specific subject matter being discussed
    - Is descriptive and self-explanatory
    - Uses professional language
    - Is specific rather than generic

    For the summary:
    - Summarize the key points in maximum two sentences
    - Focus on what was discussed, decided, or accomplished
    - Be concise but informative

    <transcript>
    {text}
    </transcript>
    """
).strip()
