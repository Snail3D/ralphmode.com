class MockStorageBackend:
    def __init__(self):
        self.db = {}

    def load_state(self, user_id):
        return self.db.get(user_id)

    def save_state(self, user_id, state_value):
        self.db[user_id] = state_value