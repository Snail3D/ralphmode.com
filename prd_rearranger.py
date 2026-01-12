from dataclasses import dataclass, field
from typing import List, Dict

@dataclass(order=True)
class Task:
    id: str
    title: str
    priority: int = 5
    dependencies: List[str] = field(default_factory=list, compare=False)

class PRDRearranger:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}

    def add_or_update_task(self, task: Task):
        self.tasks[task.id] = task

    def get_optimized_order(self) -> List[Task]:
        """
        Reorders tasks based on dependencies (topological sort) 
        and priority. Higher priority tasks come first where possible.
        """
        in_degree = {t_id: 0 for t_id in self.tasks}
        graph = {t_id: [] for t_id in self.tasks}

        for t_id, task in self.tasks.items():
            for dep_id in task.dependencies:
                if dep_id in graph:
                    graph[dep_id].append(t_id)
                    in_degree[t_id] += 1

        # Initialize queue with tasks having no dependencies
        # Sort by priority descending (highest first)
        queue = sorted(
            [t_id for t_id, degree in in_degree.items() if degree == 0],
            key=lambda x: -self.tasks[x].priority
        )

        optimized_order = []
        
        while queue:
            # Re-sort queue to ensure highest priority available task is picked
            queue.sort(key=lambda x: -self.tasks[x].priority)
            current_id = queue.pop(0)
            optimized_order.append(self.tasks[current_id])

            for neighbor in graph[current_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(optimized_order) != len(self.tasks):
            raise ValueError("Circular dependency detected in tasks.")

        return optimized_order