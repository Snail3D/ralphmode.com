from abc import ABC, abstractmethod
from typing import Dict, List


class StorageBackend(ABC):
    @abstractmethod
    def get_question(self, question_id: str) -> str:
        pass
    
    @abstractmethod
    def get_user_context(self, user_id: str) -> Dict:
        pass
    
    @abstractmethod
    def store_analysis(self, user_id: str, question_id: str, analysis: Dict):
        pass
    
    @abstractmethod
    def get_user_requirements(self, user_id: str) -> List[Dict]:
        pass


class InMemoryStorage(StorageBackend):
    def __init__(self):
        self.questions = {}
        self.user_contexts = {}
        self.analyses = {}
    
    def add_question(self, question_id: str, question: str):
        self.questions[question_id] = question
    
    def set_user_context(self, user_id: str, context: Dict):
        self.user_contexts[user_id] = context
    
    def get_question(self, question_id: str) -> str:
        return self.questions.get(question_id, "")
    
    def get_user_context(self, user_id: str) -> Dict:
        return self.user_contexts.get(user_id, {})
    
    def store_analysis(self, user_id: str, question_id: str, analysis: Dict):
        if user_id not in self.analyses:
            self.analyses[user_id] = []
        self.analyses[user_id].append({"question_id": question_id, "analysis": analysis})
    
    def get_user_requirements(self, user_id: str) -> List[Dict]:
        requirements = []
        for item in self.analyses.get(user_id, []):
            requirements.extend(item["analysis"].get("requirements", []))
        return requirements