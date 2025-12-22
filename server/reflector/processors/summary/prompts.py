"""
LLM prompts for summary generation.

Extracted to a separate module to avoid circular imports when importing
from summary_builder.py (which imports LLM/settings at module level).
"""

from textwrap import dedent


def build_participant_instructions(participant_names: list[str]) -> str:
    """Build participant context instructions for LLM prompts."""
    if not participant_names:
        return ""

    participants_list = ", ".join(participant_names)
    return dedent(
        f"""
        # IMPORTANT: Participant Names
        The following participants are identified in this conversation: {participants_list}

        You MUST use these specific participant names when referring to people in your response.
        Do NOT use generic terms like "a participant", "someone", "attendee", "Speaker 1", "Speaker 2", etc.
        Always refer to people by their actual names (e.g., "John suggested..." not "A participant suggested...").
        """
    ).strip()


DETAILED_SUBJECT_PROMPT_TEMPLATE = dedent(
    """
    Get me information about the topic "{subject}"

    # RESPONSE GUIDELINES
    Follow this structured approach to create the topic summary:
    - Highlight important arguments, insights, or data presented.
    - Outline decisions made.
    - Indicate any decisions reached, including any rationale or key factors
      that influenced these decisions.
    - Detail action items and responsibilities.
    - For each decision or unresolved issue, list specific action items agreed
      upon, along with assigned individuals or teams responsible for each task.
    - Specify deadlines or timelines if mentioned. For each action item,
      include any deadlines or timeframes discussed for completion or follow-up.
    - Mention unresolved issues or topics needing further discussion, aiding in
      planning future meetings or follow-up actions.
    - Do not include topic unrelated to {subject}.

    # OUTPUT
    Your summary should be clear, concise, and structured, covering all major
    points, decisions, and action items from the meeting. It should be easy to
    understand for someone not present, providing a comprehensive understanding
    of what transpired and what needs to be done next. The summary should not
    exceed one page to ensure brevity and focus.
    """
).strip()

PARAGRAPH_SUMMARY_PROMPT = dedent(
    """
    Summarize the mentioned topic in 1 paragraph.
    It will be integrated into the final summary, so just for this topic.
    """
).strip()

RECAP_PROMPT = dedent(
    """
    Provide a high-level quick recap of the following meeting, fitting in one paragraph.
    Do not include decisions, action items or unresolved issue, just highlight the high moments.
    Just dive into the meeting, be concise and do not include unnecessary details.
    As we already know it is a meeting, do not start with 'During the meeting' or equivalent.
    """
).strip()


def build_summary_markdown(recap: str, summaries: list[dict[str, str]]) -> str:
    """Build markdown summary from recap and subject summaries."""
    lines: list[str] = []
    if recap:
        lines.append("# Quick recap")
        lines.append("")
        lines.append(recap)
        lines.append("")

    if summaries:
        lines.append("# Summary")
        lines.append("")
        for summary in summaries:
            lines.append(f"**{summary['subject']}**")
            lines.append(summary["summary"])
            lines.append("")

    return "\n".join(lines)
