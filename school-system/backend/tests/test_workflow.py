"""Tests for the Workflow Engine."""

import uuid

import pytest

from app.services.workflow.workflow_engine import BUILTIN_WORKFLOWS


class TestWorkflowDefinitions:
    """Test built-in workflow templates."""

    def test_all_workflows_have_required_fields(self):
        for key, wf in BUILTIN_WORKFLOWS.items():
            assert "name" in wf
            assert "entity_type" in wf
            assert "states" in wf
            assert "transitions" in wf
            assert len(wf["states"]) > 0
            assert len(wf["transitions"]) > 0

    def test_workflow_states_have_initial(self):
        """Every workflow has a state with sort_order=1 as initial."""
        for key, wf in BUILTIN_WORKFLOWS.items():
            first_states = [s for s in wf["states"] if s[2] == 1]
            assert len(first_states) == 1, f"{key}: expected 1 initial state"

    def test_workflow_has_terminal_state(self):
        """Every workflow has at least one final state."""
        for key, wf in BUILTIN_WORKFLOWS.items():
            final_states = [s for s in wf["states"] if s[4] is True]
            assert len(final_states) >= 1, f"{key}: expected terminal states"

    def test_transitions_reference_valid_states(self):
        """Every transition references states that exist."""
        for key, wf in BUILTIN_WORKFLOWS.items():
            state_names = {s[0] for s in wf["states"]}
            for t in wf["transitions"]:
                assert t[0] in state_names, f"{key}: from '{t[0]}' not in states"
                assert t[1] in state_names, f"{key}: to '{t[1]}' not in states"

    def test_report_card_states(self):
        """Report card workflow has correct states."""
        wf = BUILTIN_WORKFLOWS["report_card"]
        names = [s[0] for s in wf["states"]]
        assert "draft" in names
        assert "published" in names
        assert "pending_head" in names or "pending_principal" in names

    def test_exam_publishing_flow(self):
        """Exam publishing has moderation step."""
        wf = BUILTIN_WORKFLOWS["exam_publishing"]
        names = [s[0] for s in wf["states"]]
        assert "pending_moderation" in names

    def test_promotion_flow(self):
        """Promotion has approval and rejection."""
        wf = BUILTIN_WORKFLOWS["promotion"]
        names = [s[0] for s in wf["states"]]
        assert "approved" in names
        assert "rejected" in names

    def test_attendance_lock_is_simple(self):
        """Attendance lock has just open/locked."""
        wf = BUILTIN_WORKFLOWS["attendance_lock"]
        names = [s[0] for s in wf["states"]]
        assert "open" in names
        assert "locked" in names
        assert len(wf["states"]) == 2


class TestWorkflowTransitions:
    """Test transition logic."""

    def test_no_orphan_states(self):
        """States that aren't terminal should have outgoing transitions."""
        for key, wf in BUILTIN_WORKFLOWS.items():
            terminal = {s[0] for s in wf["states"] if s[4]}
            from_states = {t[0] for t in wf["transitions"]}
            non_terminal = {s[0] for s in wf["states"] if not s[4]}

            for state in non_terminal:
                assert state in from_states, (
                    f"{key}: non-terminal state '{state}' has no outgoing transitions"
                )

    def test_role_assignment(self):
        """Each state has a required_role."""
        for key, wf in BUILTIN_WORKFLOWS.items():
            for state in wf["states"]:
                role = state[3]
                assert role in (
                    "teacher", "head_teacher", "deputy_principal",
                    "school_admin", "platform_admin"
                ), f"{key}: state '{state[0]}' has unknown role '{role}'"

    def test_transitions_have_display_names(self):
        """Every transition has display_name for UI."""
        for key, wf in BUILTIN_WORKFLOWS.items():
            for t in wf["transitions"]:
                assert len(t[3]) > 0, f"{key}: transition has empty display name"
