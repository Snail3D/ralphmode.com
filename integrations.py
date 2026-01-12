class SystemAdapter:
    """Interface for external system integration (e.g., CRM, Database)."""
    
    def log_state_change(self, old_state, new_state, context):
        # Simulate external API call or DB update
        payload = {
            "previous_state": old_state.value,
            "current_state": new_state.value,
            "metadata": context or {}
        }
        print(f"[SYNC] State updated: {payload}")
        # In production: requests.post("https://api.crm.com/update", json=payload)