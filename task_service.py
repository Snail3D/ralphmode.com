from datetime import datetime
from typing import List, Optional, Dict

class Task:
    def __init__(self, task_id: str, title: str):
        self.id = task_id
        self.title = title
        self.is_deleted = False
        self.deleted_at: Optional[datetime] = None

    def __repr__(self):
        status = "Deleted" if self.is_deleted else "Active"
        return f"<Task {self.id}: {self.title} ({status})>"

class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        self._tasks[task.id] = task

    def remove_task(self, task_id: str) -> bool:
        """Soft deletes a task, marking it as irrelevant but keeping it for restoration."""
        task = self._tasks.get(task_id)
        if task and not task.is_deleted:
            task.is_deleted = True
            task.deleted_at = datetime.utcnow()
            return True
        return False

    def restore_task(self, task_id: str) -> bool:
        """Restores a previously soft-deleted task."""
        task = self._tasks.get(task_id)
        if task and task.is_deleted:
            task.is_deleted = False
            task.deleted_at = None
            return True
        return False

    def get_active_tasks(self) -> List[Task]:
        """Returns only tasks that are not deleted."""
        return [t for t in self._tasks.values() if not t.is_deleted]

    def get_deleted_tasks(self) -> List[Task]:
        """Returns tasks currently in the trash."""
        return [t for t in self._tasks.values() if t.is_deleted]