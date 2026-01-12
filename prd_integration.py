# Mock existing system components for integration demonstration

class NotificationGateway:
    """Existing system service for sending notifications."""
    def broadcast(self, message):
        # In a real scenario, this might post to Slack, email, etc.
        print(f"Broadcasting: {message}")

class PRDService:
    """Existing system service managing Product Requirements."""
    def __init__(self):
        self.subscribers = []

    def register_observer(self, observer):
        self.subscribers.append(observer)

    def update_prd(self, feature_name, reason):
        change_data = {
            'feature': feature_name,
            'reason': reason
        }
        for observer in self.subscribers:
            observer.announce(change_data)

# Integration Logic
if __name__ == "__main__":
    # Initialize existing services
    gateway = NotificationGateway()
    prd_service = PRDService()

    # Integrate Ralph Announcer
    ralph = RalphAnnouncer(gateway)
    prd_service.register_observer(ralph)

    # Trigger a PRD change event
    prd_service.update_prd("User Authentication Flow", "Security audit requirements")