from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Callable

class OverrideCommand(Enum):
    START_BUILDING = "start building"
    MORE_QUESTIONS = "more questions"

@dataclass
class SessionState:
    config: dict
    status: str  # 'collecting', 'building', 'paused'
    step: int = 0

class OverrideController:
    def __init__(self, state: SessionState):
        self.state = state
        self._on_build_start: Optional[Callable] = None
        self._on_questions_request: Optional[Callable] = None

    def register_callbacks(self, on_build_start: Callable, on_questions_request: Callable):
        self._on_build_start = on_build_start
        self._on_questions_request = on_questions_request

    def process_input(self, user_input: str) -> bool:
        """Returns True if an override was triggered, False otherwise."""
        normalized = user_input.strip().lower()
        
        if normalized == OverrideCommand.START_BUILDING.value:
            self._handle_start_building()
            return True
        elif normalized == OverrideCommand.MORE_QUESTIONS.value:
            self._handle_more_questions()
            return True
        
        return False

    def _handle_start_building(self):
        self.state.status = 'building'
        if self._on_build_start:
            self._on_build_start(self.state.config)

    def _handle_more_questions(self):
        self.state.status = 'collecting'
        if self._on_questions_request:
            self._on_questions_request()