from discovery.machine import DiscoveryStateMachine
from discovery.states import DiscoveryState, DiscoveryEvent

class DiscoveryService:
    def __init__(self, storage_backend):
        self.storage = storage_backend

    def get_user_machine(self, user_id):
        saved_state = self.storage.load_state(user_id)
        if not saved_state:
            return DiscoveryStateMachine()
        return DiscoveryStateMachine(DiscoveryState(saved_state))

    def advance_flow(self, user_id, event):
        machine = self.get_user_machine(user_id)
        
        try:
            event_enum = DiscoveryEvent(event)
        except ValueError:
            raise ValueError(f"Invalid event: {event}")

        if machine.trigger(event_enum):
            self.storage.save_state(user_id, machine.state.value)
            return machine.state.value
        else:
            raise ValueError(f"Transition not allowed from {machine.state.name} with {event.name}")