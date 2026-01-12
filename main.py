from core.overrides import OverrideController, SessionState

class Application:
    def __init__(self):
        self.state = SessionState(config={}, status='collecting')
        self.controller = OverrideController(self.state)
        self.controller.register_callbacks(
            on_build_start=self.initiate_build,
            on_questions_request=self.resume_questions
        )

    def run(self):
        print("System ready. Type 'more questions' or 'start building' at any time.")
        
        while True:
            if self.state.status == 'collecting':
                user_input = input(f"Step {self.state.step}: Enter config value: ")
                if self.controller.process_input(user_input):
                    continue
                self._update_config(user_input)
            
            elif self.state.status == 'building':
                print("Building project...")
                user_input = input("Press Enter to finish or type 'more questions': ")
                if self.controller.process_input(user_input):
                    continue
                break
            
            elif self.state.status == 'paused':
                break

    def _update_config(self, value: str):
        self.state.config[f'param_{self.state.step}'] = value
        self.state.step += 1
        if self.state.step >= 3:
            print("Auto-proceeding to build phase.")
            self.controller.process_input("start building")

    def initiate_build(self, current_config: dict):
        print(f"[OVERRIDE] Initiating build with config: {current_config}")

    def resume_questions(self):
        print(f"[OVERRIDE] Resuming questions at step {self.state.step}.")

if __name__ == "__main__":
    app = Application()
    app.run()