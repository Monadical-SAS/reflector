"""Pydantic models for summary processing."""

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    """A single action item from the meeting"""

    task: str = Field(description="The task or action item to be completed")
    assigned_to: str | None = Field(
        default=None, description="Person or team assigned to this task (name)"
    )
    assigned_to_participant_id: str | None = Field(
        default=None, description="Participant ID if assigned_to matches a participant"
    )
    deadline: str | None = Field(
        default=None, description="Deadline or timeframe mentioned for this task"
    )
    context: str | None = Field(
        default=None, description="Additional context or notes about this task"
    )


class Decision(BaseModel):
    """A decision made during the meeting"""

    decision: str = Field(description="What was decided")
    rationale: str | None = Field(
        default=None,
        description="Reasoning or key factors that influenced this decision",
    )
    decided_by: str | None = Field(
        default=None, description="Person or group who made the decision (name)"
    )
    decided_by_participant_id: str | None = Field(
        default=None, description="Participant ID if decided_by matches a participant"
    )


class ActionItemsResponse(BaseModel):
    """Pydantic model for identified action items"""

    decisions: list[Decision] = Field(
        default_factory=list,
        description="List of decisions made during the meeting",
    )
    next_steps: list[ActionItem] = Field(
        default_factory=list,
        description="List of action items and next steps to be taken",
    )
