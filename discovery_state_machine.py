from enum import Enum, auto
from typing import Dict, Optional, Callable, Any

class DiscoveryState(Enum):
    INITIAL = auto()
    GREETING = auto()
    QUALIFICATION = auto()
    NEEDS_ANALYSIS = auto()
    PROPOSAL = auto()
    NEGOTIATION = auto()
    CLOSED_WON = auto()
    CLOSED_LOST = auto()

class DiscoveryStateMachine:
    def __init__(self):
        self.state = DiscoveryState.INITIAL
        self.context: Dict[str, Any] = {}
        self._transitions: Dict[DiscoveryState, Dict[str, DiscoveryState]] = {
            DiscoveryState.INITIAL: {
                "start": DiscoveryState.GREETING
            },
            DiscoveryState.GREETING: {
                "acknowledge": DiscoveryState.QUALIFICATION
            },
            DiscoveryState.QUALIFICATION: {
                "qualified": DiscoveryState.NEEDS_ANALYSIS,
                "disqualified": DiscoveryState.CLOSED_LOST
            },
            DiscoveryState.NEEDS_ANALYSIS: {
                "complete": DiscoveryState.PROPOSAL
            },
            DiscoveryState.PROPOSAL: {
                "interested": DiscoveryState.NEGOTIATION,
                "rejected": DiscoveryState.CLOSED_LOST
            },
            DiscoveryState.NEGOTIATION: {
                "agree": DiscoveryState.CLOSED_WON,
                "reject": DiscoveryState.CLOSED_LOST
            },
            DiscoveryState.CLOSED_WON: {},
            DiscoveryState.CLOSED_LOST: {}
        }

    def transition(self, event: str) -> bool:
        if self.state not in self._transitions:
            return False
        
        possible_transitions = self._transitions[self.state]
        
        if event in possible_transitions:
            self.state = possible_transitions[event]
            return True
        
        return False

    def get_state(self) -> DiscoveryState:
        return self.state

    def update_context(self, key: str, value: Any) -> None:
        self.context[key] = value

    def get_context(self) -> Dict[str, Any]:
        return self.context

    def reset(self) -> None:
        self.state = DiscoveryState.INITIAL
        self.context.clear()