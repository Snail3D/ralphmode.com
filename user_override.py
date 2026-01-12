from typing import Protocol, Optional

class BuildSystem(Protocol):
    def start(self) -> None: ...

class QuestionSystem(Protocol):
    def resume(self) -> None: ...

class UserOverrideHandler:
    """
    Handles specific user override commands to alter the application flow.
    """
    
    COMMAND_START_BUILDING = "start building"
    COMMAND_MORE_QUESTIONS = "more questions"

    def __init__(self, build_sys: Optional[BuildSystem] = None, question_sys: Optional[QuestionSystem] = None):
        self.build_sys = build_sys
        self.question_sys = question_sys

    def process(self, user_input: str) -> bool:
        """
        Processes user text. Returns True if a command was handled, False otherwise.
        """
        if not user_input:
            return False

        normalized = user_input.strip().lower()

        if normalized == self.COMMAND_START_BUILDING:
            self._trigger_build()
            return True
        
        if normalized == self.COMMAND_MORE_QUESTIONS:
            self._trigger_questions()
            return True
            
        return False

    def _trigger_build(self) -> None:
        if self.build_sys:
            self.build_sys.start()

    def _trigger_questions(self) -> None:
        if self.question_sys:
            self.question_sys.resume()