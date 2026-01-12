from enum import Enum

class DiscoveryState(Enum):
    INIT = "init"
    GREETING = "greeting"
    REQUIREMENTS = "requirements"
    QUALIFICATION = "qualification"
    PROPOSAL = "proposal"
    CLOSED = "closed"
    ERROR = "error"