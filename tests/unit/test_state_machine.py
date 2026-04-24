"""Unit tests for JobStateMachine and CoverStateMachine.

Covers every valid and invalid transition for both state machines, terminal
state detection, and the InvalidStateTransitionError exception contract.
"""
from __future__ import annotations

import pytest

from app.domain.state_machine import (
    CoverStateMachine,
    CoverStatus,
    InvalidStateTransitionError,
    JobStateMachine,
    JobStatus,
    cover_state_machine,
    job_state_machine,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def jsm() -> JobStateMachine:
    return JobStateMachine()


@pytest.fixture()
def csm() -> CoverStateMachine:
    return CoverStateMachine()


# ---------------------------------------------------------------------------
# JobStateMachine — valid transitions (can_transition returns True)
# ---------------------------------------------------------------------------

JOB_VALID_TRANSITIONS = [
    ("queued", "generating"),
    ("queued", "paused"),
    ("queued", "cancelled"),
    ("generating", "awaiting_cover_approval"),
    ("generating", "assembling"),
    ("generating", "paused"),
    ("generating", "cancelled"),
    ("generating", "failed"),
    ("awaiting_cover_approval", "assembling"),
    ("awaiting_cover_approval", "generating"),
    ("assembling", "complete"),
    ("assembling", "failed"),
    ("paused", "queued"),
    ("paused", "cancelled"),
    ("failed", "queued"),
]


@pytest.mark.parametrize("current,target", JOB_VALID_TRANSITIONS)
def test_job_can_transition_valid(jsm: JobStateMachine, current: str, target: str) -> None:
    assert jsm.can_transition(current, target) is True


@pytest.mark.parametrize("current,target", JOB_VALID_TRANSITIONS)
def test_job_validate_transition_does_not_raise_for_valid(
    jsm: JobStateMachine, current: str, target: str
) -> None:
    jsm.validate_transition(current, target)  # must not raise


# ---------------------------------------------------------------------------
# JobStateMachine — invalid transitions (can_transition returns False)
# ---------------------------------------------------------------------------

JOB_INVALID_TRANSITIONS = [
    ("complete", "queued"),
    ("complete", "generating"),
    ("complete", "paused"),
    ("complete", "cancelled"),
    ("cancelled", "queued"),
    ("cancelled", "generating"),
    ("cancelled", "paused"),
    ("queued", "complete"),
    ("queued", "assembling"),
    ("queued", "failed"),
    ("assembling", "queued"),
    ("assembling", "paused"),
    ("paused", "generating"),
    ("paused", "complete"),
    ("failed", "complete"),
    ("failed", "cancelled"),
]


@pytest.mark.parametrize("current,target", JOB_INVALID_TRANSITIONS)
def test_job_can_transition_invalid(jsm: JobStateMachine, current: str, target: str) -> None:
    assert jsm.can_transition(current, target) is False


@pytest.mark.parametrize("current,target", JOB_INVALID_TRANSITIONS)
def test_job_validate_transition_raises_for_invalid(
    jsm: JobStateMachine, current: str, target: str
) -> None:
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        jsm.validate_transition(current, target)
    err = exc_info.value
    assert err.current == current
    assert err.target == target
    assert isinstance(err.valid_transitions, list)


# ---------------------------------------------------------------------------
# JobStateMachine — terminal state detection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", ["complete", "cancelled"])
def test_job_is_terminal_true(jsm: JobStateMachine, status: str) -> None:
    assert jsm.is_terminal(status) is True


@pytest.mark.parametrize("status", ["queued", "generating", "paused", "failed", "assembling", "awaiting_cover_approval"])
def test_job_is_terminal_false(jsm: JobStateMachine, status: str) -> None:
    assert jsm.is_terminal(status) is False


# ---------------------------------------------------------------------------
# JobStateMachine — unknown state
# ---------------------------------------------------------------------------

def test_job_unknown_state_cannot_transition(jsm: JobStateMachine) -> None:
    assert jsm.can_transition("unknown_state", "queued") is False


def test_job_unknown_state_raises_with_empty_valid_transitions(jsm: JobStateMachine) -> None:
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        jsm.validate_transition("unknown_state", "queued")
    assert exc_info.value.valid_transitions == []


# ---------------------------------------------------------------------------
# CoverStateMachine — valid transitions
# ---------------------------------------------------------------------------

COVER_VALID_TRANSITIONS = [
    ("pending", "generating"),
    ("generating", "awaiting_approval"),
    ("generating", "failed"),
    ("awaiting_approval", "approved"),
    ("awaiting_approval", "revising"),
    ("revising", "generating"),
    ("failed", "generating"),
]


@pytest.mark.parametrize("current,target", COVER_VALID_TRANSITIONS)
def test_cover_can_transition_valid(csm: CoverStateMachine, current: str, target: str) -> None:
    assert csm.can_transition(current, target) is True


@pytest.mark.parametrize("current,target", COVER_VALID_TRANSITIONS)
def test_cover_validate_transition_does_not_raise_for_valid(
    csm: CoverStateMachine, current: str, target: str
) -> None:
    csm.validate_transition(current, target)  # must not raise


# ---------------------------------------------------------------------------
# CoverStateMachine — invalid transitions
# ---------------------------------------------------------------------------

COVER_INVALID_TRANSITIONS = [
    ("approved", "revising"),
    ("approved", "generating"),
    ("approved", "awaiting_approval"),
    ("pending", "approved"),
    ("pending", "awaiting_approval"),
    ("generating", "approved"),
    ("generating", "revising"),
    ("awaiting_approval", "pending"),
    ("awaiting_approval", "failed"),
    ("revising", "approved"),
    ("revising", "awaiting_approval"),
    ("failed", "approved"),
    ("failed", "awaiting_approval"),
]


@pytest.mark.parametrize("current,target", COVER_INVALID_TRANSITIONS)
def test_cover_can_transition_invalid(csm: CoverStateMachine, current: str, target: str) -> None:
    assert csm.can_transition(current, target) is False


@pytest.mark.parametrize("current,target", COVER_INVALID_TRANSITIONS)
def test_cover_validate_transition_raises_for_invalid(
    csm: CoverStateMachine, current: str, target: str
) -> None:
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        csm.validate_transition(current, target)
    err = exc_info.value
    assert err.current == current
    assert err.target == target
    assert isinstance(err.valid_transitions, list)


# ---------------------------------------------------------------------------
# CoverStateMachine — terminal state detection
# ---------------------------------------------------------------------------

def test_cover_is_terminal_approved(csm: CoverStateMachine) -> None:
    assert csm.is_terminal("approved") is True


@pytest.mark.parametrize("status", ["pending", "generating", "awaiting_approval", "revising", "failed"])
def test_cover_is_terminal_false(csm: CoverStateMachine, status: str) -> None:
    assert csm.is_terminal(status) is False


# ---------------------------------------------------------------------------
# CoverStateMachine — unknown state
# ---------------------------------------------------------------------------

def test_cover_unknown_state_cannot_transition(csm: CoverStateMachine) -> None:
    assert csm.can_transition("unknown_state", "approved") is False


def test_cover_unknown_state_raises_with_empty_valid_transitions(csm: CoverStateMachine) -> None:
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        csm.validate_transition("unknown_state", "approved")
    assert exc_info.value.valid_transitions == []


# ---------------------------------------------------------------------------
# InvalidStateTransitionError — exception contract
# ---------------------------------------------------------------------------

def test_invalid_state_transition_error_attributes() -> None:
    err = InvalidStateTransitionError(
        current="complete",
        target="queued",
        valid_transitions=[],
    )
    assert err.current == "complete"
    assert err.target == "queued"
    assert err.valid_transitions == []
    assert "complete" in str(err)
    assert "queued" in str(err)


def test_invalid_state_transition_error_valid_transitions_populated() -> None:
    err = InvalidStateTransitionError(
        current="queued",
        target="complete",
        valid_transitions=["generating", "paused", "cancelled"],
    )
    assert set(err.valid_transitions) == {"generating", "paused", "cancelled"}


# ---------------------------------------------------------------------------
# Enum str-compatibility (DB / JSON serialisation)
# ---------------------------------------------------------------------------

def test_job_status_is_str() -> None:
    assert isinstance(JobStatus.QUEUED, str)
    assert JobStatus.QUEUED == "queued"


def test_cover_status_is_str() -> None:
    assert isinstance(CoverStatus.APPROVED, str)
    assert CoverStatus.APPROVED == "approved"


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

def test_module_singletons_are_correct_types() -> None:
    assert isinstance(job_state_machine, JobStateMachine)
    assert isinstance(cover_state_machine, CoverStateMachine)
