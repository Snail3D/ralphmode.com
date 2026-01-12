from enum import Enum

class DiscoveryState(Enum):
    INITIAL = "initial"
    GREETING = "greeting"
    QUALIFICATION = "qualification"
    ANALYSIS = "analysis"
    PROPOSAL = "proposal"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"

class DiscoveryMachine:
    def __init__(self, integration_adapter):
        self.state = DiscoveryState.INITIAL
        self.adapter = integration_adapter

    def transition(self, new_state, context=None):
        if self._is_valid_transition(new_state):
            old_state = self.state
            self.state = new_state
            self.adapter.log_state_change(old_state, new_state, context)
            return True
        raise ValueError(f"Invalid transition from {self.state.name} to {new_state.name}")

    def _is_valid_transition(self, new_state):
        valid_paths = {
            DiscoveryState.INITIAL: [DiscoveryState.GREETING],
            DiscoveryState.GREETING: [DiscoveryState.QUALIFICATION, DiscoveryState.CLOSED_LOST],
            DiscoveryState.QUALIFICATION: [DiscoveryState.ANALYSIS, DiscoveryState.CLOSED_LOST],
            DiscoveryState.ANALYSIS: [DiscoveryState.PROPOSAL, DiscoveryState.CLOSED_LOST],
            DiscoveryState.PROPOSAL: [DiscoveryState.CLOSED_WON, DiscoveryState.CLOSED_LOST],
            DiscoveryState.CLOSED_WON: [],
            DiscoveryState.CLOSED_LOST: []
        }
        return new_state in valid_paths.get(self.state, [])