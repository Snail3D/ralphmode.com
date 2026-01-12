from dataclasses import dataclass
from typing import List

@dataclass
class Task:
    id: str
    description: str
    uncertainty: int = 100  # 0 (fully understood) to 100 (unknown)
    priority: int = 1       # 1 (low) to 10 (high)

class PRDManager:
    def __init__(self):
        self.tasks: List[Task] = []

    def add_task(self, task: Task):
        self.tasks.append(task)

    def update_understanding(self, task_id: str, knowledge_gained: int):
        """Reduces uncertainty as project understanding grows."""
        for task in self.tasks:
            if task.id == task_id:
                task.uncertainty = max(0, task.uncertainty - knowledge_gained)
                break

    def get_optimized_order(self) -> List[Task]:
        """
        Reorders tasks dynamically.
        Logic: High priority tasks first. 
        Among equal priority, better understood tasks (lower uncertainty) are prioritized for execution.
        """
        return sorted(self.tasks, key=lambda t: (-t.priority, t.uncertainty))