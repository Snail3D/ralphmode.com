class JobAnxiety:
    """
    PD-017: Ralph's Job Anxiety Trait
    Ralph is scared of losing job 'in this economy'
    """
    def __init__(self):
        self.triggers = ["economy", "recession", "budget cuts", "hiring freeze", "layoffs"]

    def handle_stimulus(self, stimulus, character):
        stimulus_lower = stimulus.lower()
        
        # Direct trigger based on keywords
        if any(trigger in stimulus_lower for trigger in self.triggers):
            return f"{character.name} looks terrified and mutters about losing their job in this economy."
        
        # General work context trigger
        if "work" in stimulus_lower or "boss" in stimulus_lower:
            return f"{character.name} nervously checks their bank account, worried about the economy."
        
        return None