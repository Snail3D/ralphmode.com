from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import uuid

@dataclass
class Task:
    id: str
    title: str
    description: str
    status: str = "Pending"
    created_at: datetime = field(default_factory=datetime.now)

class PRDSystem:
    """Existing system integration point."""
    def __init__(self):
        self._tasks: List[Task] = []

    def get_all_tasks(self) -> List[Task]:
        return self._tasks

    def add_task(self, task: Task):
        self._tasks.append(task)

class DynamicTaskFeature:
    """
    [PD-009] PRD Task Addition During Discovery
    Adds tasks dynamically as requirements emerge.
    """
    
    def __init__(self, prd_system: PRDSystem):
        self.prd_system = prd_system

    def create_discovery_task(self, title: str, description: str) -> Task:
        """
        Creates and appends a new task to the PRD during the discovery phase.
        """
        task_id = str(uuid.uuid4())[:8].upper()
        
        new_task = Task(
            id=task_id,
            title=title,
            description=description,
            status="Discovery"
        )
        
        # Integrate with existing system
        self.prd_system.add_task(new_task)
        
        return new_task