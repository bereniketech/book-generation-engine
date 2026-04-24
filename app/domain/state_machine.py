"""Job and Cover state machines — pure domain logic, no I/O."""
from __future__ import annotations

from enum import Enum
from typing import ClassVar


class JobStatus(str, Enum):
    """All valid job statuses.

    Inherits ``str`` so values are JSON-serialisable and DB-compatible without
    calling ``.value``.
    """

    QUEUED = "queued"
    GENERATING = "generating"
    AWAITING_COVER_APPROVAL = "awaiting_cover_approval"
    ASSEMBLING = "assembling"
    COMPLETE = "complete"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FAILED = "failed"


class CoverStatus(str, Enum):
    """All valid cover statuses."""

    PENDING = "pending"
    GENERATING = "generating"
    AWAITING_APPROVAL = "awaiting_approval"
    REVISING = "revising"
    APPROVED = "approved"
    FAILED = "failed"


class InvalidStateTransitionError(Exception):
    """Raised by a state machine when a requested transition is not allowed.

    Callers (API routes) should catch this and map it to the HTTP exception
    ``InvalidStateTransitionError`` defined in ``app.infrastructure.http_exceptions``.
    """

    def __init__(
        self,
        current: str,
        target: str,
        valid_transitions: list[str],
    ) -> None:
        self.current = current
        self.target = target
        self.valid_transitions = valid_transitions
        super().__init__(
            f"Cannot transition from '{current}' to '{target}'. "
            f"Valid transitions: {valid_transitions}"
        )


class JobStateMachine:
    """State machine for job lifecycle transitions.

    All state is stored in the DB; this class is stateless and holds only the
    transition table.
    """

    VALID_TRANSITIONS: ClassVar[dict[str, list[str]]] = {
        JobStatus.QUEUED: [JobStatus.GENERATING, JobStatus.PAUSED, JobStatus.CANCELLED],
        JobStatus.GENERATING: [
            JobStatus.AWAITING_COVER_APPROVAL,
            JobStatus.ASSEMBLING,
            JobStatus.PAUSED,
            JobStatus.CANCELLED,
            JobStatus.FAILED,
        ],
        JobStatus.AWAITING_COVER_APPROVAL: [JobStatus.ASSEMBLING, JobStatus.GENERATING],
        JobStatus.ASSEMBLING: [JobStatus.COMPLETE, JobStatus.FAILED],
        JobStatus.PAUSED: [JobStatus.QUEUED, JobStatus.CANCELLED],
        JobStatus.COMPLETE: [],
        JobStatus.CANCELLED: [],
        JobStatus.FAILED: [JobStatus.QUEUED],
    }

    TERMINAL_STATES: ClassVar[frozenset[str]] = frozenset(
        {JobStatus.COMPLETE, JobStatus.CANCELLED}
    )

    def can_transition(self, current: str, target: str) -> bool:
        """Return ``True`` if the transition ``current → target`` is allowed."""
        allowed = self.VALID_TRANSITIONS.get(current, [])
        return target in allowed

    def validate_transition(self, current: str, target: str) -> None:
        """Raise :exc:`InvalidStateTransitionError` if the transition is not allowed."""
        if not self.can_transition(current, target):
            allowed = self.VALID_TRANSITIONS.get(current, [])
            raise InvalidStateTransitionError(
                current=current,
                target=target,
                valid_transitions=list(allowed),
            )

    def is_terminal(self, status: str) -> bool:
        """Return ``True`` if *status* is a terminal state (no further transitions)."""
        return status in self.TERMINAL_STATES


class CoverStateMachine:
    """State machine for cover approval lifecycle transitions."""

    VALID_TRANSITIONS: ClassVar[dict[str, list[str]]] = {
        CoverStatus.PENDING: [CoverStatus.GENERATING],
        CoverStatus.GENERATING: [CoverStatus.AWAITING_APPROVAL, CoverStatus.FAILED],
        CoverStatus.AWAITING_APPROVAL: [CoverStatus.APPROVED, CoverStatus.REVISING],
        CoverStatus.REVISING: [CoverStatus.GENERATING],
        CoverStatus.APPROVED: [],
        CoverStatus.FAILED: [CoverStatus.GENERATING],
    }

    TERMINAL_STATES: ClassVar[frozenset[str]] = frozenset({CoverStatus.APPROVED})

    def can_transition(self, current: str, target: str) -> bool:
        """Return ``True`` if the transition ``current → target`` is allowed."""
        allowed = self.VALID_TRANSITIONS.get(current, [])
        return target in allowed

    def validate_transition(self, current: str, target: str) -> None:
        """Raise :exc:`InvalidStateTransitionError` if the transition is not allowed."""
        if not self.can_transition(current, target):
            allowed = self.VALID_TRANSITIONS.get(current, [])
            raise InvalidStateTransitionError(
                current=current,
                target=target,
                valid_transitions=list(allowed),
            )

    def is_terminal(self, status: str) -> bool:
        """Return ``True`` if *status* is a terminal state (no further transitions)."""
        return status in self.TERMINAL_STATES


# Module-level singletons — import and use directly.
job_state_machine = JobStateMachine()
cover_state_machine = CoverStateMachine()
