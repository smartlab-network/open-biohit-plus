from typing import Optional

class OperationSession:
    """State container for building an operation in the wizard"""

    def __init__(self, operation_key: str, config: dict):
        self.operation_key = operation_key
        self.config = config
        self.selections = {}  # Store user choices: {'volume': 100, 'source_labware': <obj>, ...}
        self.current_step_idx = 0
        self.came_from_back = False

    def current_step(self) -> Optional[str]:
        """Get the current step name, or None if finished"""
        if self.current_step_idx < len(self.config['parts']):
            return self.config['parts'][self.current_step_idx]
        return None

    def store(self, key: str, value):
        """Store a user selection"""
        self.selections[key] = value

    def advance(self):
        """Move to next step"""
        self.current_step_idx += 1
        self.came_from_back = False

    def go_back(self):
        """Go back one step (for future 'Back' button feature)"""
        if self.current_step_idx > 0:
            self.current_step_idx -= 1
            # Clear the selection we're backing out of
            current_step_key = self.config['parts'][self.current_step_idx]
            if current_step_key in self.selections:
                del self.selections[current_step_key]
            self.came_from_back = True
            return True
        return False

    def is_complete(self) -> bool:
        """Check if all steps are done"""
        return self.current_step() is None

    def get_progress(self) -> str:
        """Get progress string like 'Step 2 of 5'"""
        total = len(self.config['parts'])
        current = min(self.current_step_idx + 1, total)
        return f"Step {current} of {total}"

