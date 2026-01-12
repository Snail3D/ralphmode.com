from enum import Enum

class DiscoveryState(Enum):
    INITIAL = "initial"
    GATHERING_REQUIREMENTS = "gathering_requirements"
    ANALYZING = "analyzing"
    PROPOSING = "proposing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class DiscoveryEvent(Enum):
    START = "start"
    REQUIREMENTS_MET = "requirements_met"
    ANALYSIS_COMPLETE = "analysis_complete"
    PROPOSAL_ACCEPTED = "proposal_accepted"
    CANCEL = "cancel"
    RESET = "reset"