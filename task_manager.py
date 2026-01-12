import uuid
from typing import List, Dict, Optional

class Task:
    def __init__(self, title: str, description: str = ""):
        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.is_removed = False

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "is_removed": self.is_removed
        }

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}

    def add_task(self, title: str, description: str = "") -> Task:
        task = Task(title, description)
        self.tasks[task.id] = task
        return task

    def remove_task(self, task_id: str) -> bool:
        """Soft remove a task by marking it as removed."""
        task = self.tasks.get(task_id)
        if task:
            task.is_removed = True
            return True
        return False

    def restore_task(self, task_id: str) -> bool:
        """Restore a previously removed task."""
        task = self.tasks.get(task_id)
        if task and task.is_removed:
            task.is_removed = False
            return True
        return False

    def get_active_tasks(self) -> List[Dict]:
        return [t.to_dict() for t in self.tasks.values() if not t.is_removed]

    def get_removed_tasks(self) -> List[Dict]:
        return [t.to_dict() for t in self.tasks.values() if t.is_removed]

    def permanent_delete(self, task_id: str) -> bool:
        """Permanently remove task from system."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False