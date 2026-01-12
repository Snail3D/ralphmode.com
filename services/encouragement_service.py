from typing import Protocol
from .complexity_calculator import ComplexityCalculator

class NotificationService(Protocol):
    def send_discussion_prompt(self, project_id: int, channel: str, message: str): ...

class EncouragementService:
    THRESHOLD = 60

    def __init__(self, notifier: NotificationService):
        self.notifier = notifier

    def evaluate_and_prompt(self, project) -> bool:
        """
        Evaluates project complexity and sends a prompt if necessary.
        Returns True if a prompt was sent.
        """
        score = ComplexityCalculator.calculate(project)
        
        if score >= self.THRESHOLD:
            msg = (
                f"Complexity Alert: Project '{project.title}' scored {score}/100. "
                "Given the complexity, we recommend a dedicated architecture discussion."
            )
            self.notifier.send_discussion_prompt(
                project_id=project.id,
                channel=project.team_channel,
                message=msg
            )
            return True
        return False