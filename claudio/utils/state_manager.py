"""State management utilities for persisting workflow state."""

import json
from pathlib import Path
from typing import Optional

import aiofiles

from claudio.config import get_session_state_file
from claudio.models.workflow_state import WorkflowState


class StateManager:
    """Manages persistence of workflow state."""

    @staticmethod
    async def save_state(state: WorkflowState) -> None:
        """Save workflow state to disk.

        Args:
            state: The workflow state to save
        """
        state_file = get_session_state_file(state.session_id)

        # Ensure parent directory exists
        state_file.parent.mkdir(parents=True, exist_ok=True)

        # Serialize to JSON
        state_dict = state.model_dump(mode="json")

        # Write to file
        async with aiofiles.open(state_file, "w") as f:
            await f.write(json.dumps(state_dict, indent=2, default=str))

    @staticmethod
    async def load_state(session_id: str) -> Optional[WorkflowState]:
        """Load workflow state from disk.

        Args:
            session_id: The session identifier

        Returns:
            The workflow state if found, None otherwise
        """
        state_file = get_session_state_file(session_id)

        if not state_file.exists():
            return None

        # Read from file
        async with aiofiles.open(state_file, "r") as f:
            content = await f.read()
            state_dict = json.loads(content)

        # Deserialize
        return WorkflowState(**state_dict)

    @staticmethod
    def state_exists(session_id: str) -> bool:
        """Check if state file exists for a session.

        Args:
            session_id: The session identifier

        Returns:
            True if state file exists, False otherwise
        """
        state_file = get_session_state_file(session_id)
        return state_file.exists()

    @staticmethod
    async def delete_state(session_id: str) -> bool:
        """Delete state file for a session.

        Args:
            session_id: The session identifier

        Returns:
            True if deleted, False if not found
        """
        state_file = get_session_state_file(session_id)

        if not state_file.exists():
            return False

        state_file.unlink()
        return True

    @staticmethod
    def list_sessions() -> list[str]:
        """List all session IDs that have state files.

        Returns:
            List of session IDs
        """
        from claudio.config import config

        sessions_dir = config.workspace_dir / "sessions"

        if not sessions_dir.exists():
            return []

        # Find all directories with state.json
        sessions = []
        for session_dir in sessions_dir.iterdir():
            if session_dir.is_dir():
                state_file = session_dir / "state.json"
                if state_file.exists():
                    sessions.append(session_dir.name)

        return sorted(sessions)
