from discovery import DiscoveryMachine, DiscoveryState
from integrations import SystemAdapter

if __name__ == "__main__":
    # Initialize with integration adapter
    crm_adapter = SystemAdapter()
    machine = DiscoveryMachine(crm_adapter)

    # Simulate conversation flow
    try:
        machine.transition(DiscoveryState.GREETING, {"user_id": 101, "msg": "Hello"})
        machine.transition(DiscoveryState.QUALIFICATION, {"budget": "10k"})
        machine.transition(DiscoveryState.ANALYSIS, {"requirements": ["API", "Dashboard"]})
        machine.transition(DiscoveryState.PROPOSAL)
        machine.transition(DiscoveryState.CLOSED_WON, {"contract_value": 10000})
    except ValueError as e:
        print(f"Flow Error: {e}")