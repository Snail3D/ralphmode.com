from typing import Dict, Optional
from .states import DiscoveryState

class DiscoveryMachine:
    def __init__(self):
        self.state = DiscoveryState.INIT
        self.context: Dict = {}
        self._transitions: Dict[DiscoveryState, Dict[str, DiscoveryState]] = {
            DiscoveryState.INIT: {"start": DiscoveryState.GREETING},
            DiscoveryState.GREETING: {"provide_details": DiscoveryState.REQUIREMENTS},
            DiscoveryState.REQUIREMENTS: {"clarify": DiscoveryState.QUALIFICATION},
            DiscoveryState.QUALIFICATION: {"approve": DiscoveryState.PROPOSAL, "reject": DiscoveryState.CLOSED},
            DiscoveryState.PROPOSAL: {"accept": DiscoveryState.CLOSED, "decline": DiscoveryState.CLOSED},
            DiscoveryState.CLOSED: {"reset": DiscoveryState.INIT},
        }

    def transition(self, event: str, payload: Optional[Dict] = None) -> bool:
        if self.state not in self._transitions:
            return False
        if event not in self._transitions[self.state]:
            return False

        self.state = self._transitions[self.state][event]
        if payload:
            self.context.update(payload)
        return True

    def get_state(self) -> DiscoveryState:
        return self.state