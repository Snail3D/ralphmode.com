from services.encouragement_service import EncouragementService
from utils.slack_notifier import SlackNotifier # Hypothetical existing system

# Initialize service with existing infrastructure
_notifier = SlackNotifier()
_encouragement_service = EncouragementService(_notifier)

def on_project_created_or_updated(sender, instance, **kwargs):
    """
    Signal handler to trigger complexity check on project save.
    Integrate with Django signals or equivalent event system.
    """
    # Only trigger if status is active/draft to avoid spamming closed projects
    if instance.status in ['planning', 'active']:
        _encouragement_service.evaluate_and_prompt(instance)