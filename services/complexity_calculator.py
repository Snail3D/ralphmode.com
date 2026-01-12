import re

class ComplexityCalculator:
    """
    Analyzes project attributes to determine a complexity score.
    Score 0-100.
    """
    
    KEYWORDS = {
        'high': ['distributed', 'scalable', 'machine learning', 'ai', 'blockchain', 'real-time'],
        'medium': ['api', 'database', 'integration', 'authentication']
    }

    @staticmethod
    def calculate(project) -> int:
        score = 0
        
        # 1. Description length factor (max 20 points)
        desc_len = len(project.description or "")
        score += min(desc_len // 50, 20)

        # 2. Dependency count factor (max 30 points)
        score += min(len(project.dependencies) * 5, 30)

        # 3. Keyword analysis (max 50 points)
        text = (project.title + " " + (project.description or "")).lower()
        for word in ComplexityCalculator.KEYWORDS['high']:
            if word in text:
                score += 10
        for word in ComplexityCalculator.KEYWORDS['medium']:
            if word in text:
                score += 5

        return min(score, 100)