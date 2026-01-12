from discovery.states import DiscoveryState, DiscoveryEvent

class DiscoveryStateMachine:
    def __init__(self, initial_state=DiscoveryState.INITIAL):
        self.state = initial_state
        self._transitions = {
            DiscoveryState.INITIAL: {
                DiscoveryEvent.START: DiscoveryState.GATHERING_REQUIREMENTS
            },
            DiscoveryState.GATHERING_REQUIREMENTS: {
                DiscoveryEvent.REQUIREMENTS_MET: DiscoveryState.ANALYZING,
                DiscoveryEvent.CANCEL: DiscoveryState.CANCELLED
            },
            DiscoveryState.ANALYZING: {
                DiscoveryEvent.ANALYSIS_COMPLETE: DiscoveryState.PROPOSING,
                DiscoveryEvent.CANCEL: DiscoveryState.CANCELLED
            },
            DiscoveryState.PROPOSING: {
                DiscoveryEvent.PROPOSAL_ACCEPTED: DiscoveryState.COMPLETED,
                DiscoveryEvent.CANCEL: DiscoveryState.CANCELLED
            },
            DiscoveryState.COMPLETED: {
                DiscoveryEvent.RESET: DiscoveryState.INITIAL
            },
            DiscoveryState.CANCELLED: {
                DiscoveryEvent.RESET: DiscoveryState.INITIAL
            }
        }

    def trigger(self, event):
        if self.state in self._transitions and event in self._transitions[self.state]:
            self.state = self._transitions[self.state][event]
            return True
        return False

    def get_state(self):
        return self.state