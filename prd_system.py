from dataclasses import dataclass, field
from typing import List
from datetime import datetime

@dataclass
class Task:
    id: str
    title: str
    description: str
    status: str = "Pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

class PRDManager:
    def __init__(self):
        self.tasks: List[Task] = []

    def add_task(self, title: str, description: str) -> Task:
        """Dynamically adds a new task to the PRD as requirements emerge."""
        task_id = f"TASK-{len(self.tasks) + 1:03d}"
        new_task = Task(id=task_id, title=title, description=description)
        self.tasks.append(new_task)
        return new_task

    def get_tasks(self) -> List[Task]:
        return self.tasks

# Example usage
if __name__ == "__main__":
    manager = PRDManager()
    manager.add_task("Implement Auth", "Add OAuth2 support")
    manager.add_task("Database Migration", "Migrate user data to PostgreSQL")
    
    for task in manager.get_tasks():
        print(f"{task.id}: {task.title} - {task.status}")