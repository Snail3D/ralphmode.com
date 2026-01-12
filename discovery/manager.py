from typing import Dict, Any
from .machine import DiscoveryMachine
from .states import DiscoveryState

class DiscoveryManager:
    def __init__(self):
        self.machine = DiscoveryMachine()
        self.session_data: Dict[str, Any] = {}

    def process_event(self, event: str, data: Dict = None) -> Dict[str, Any]:
        success = self.machine.transition(event, data)
        return {
            "success": success,
            "current_state": self.machine.get_state().value,
            "context": self.machine.context
        }

    def get_current_phase(self) -> str:
        return self.machine.get_state().value