class Phase1McpStubClient:
    """Phase 1 must not perform any external writes."""

    def __init__(self) -> None:
        self.write_attempts: int = 0

    def create_hold(self, *_args, **_kwargs) -> str:
        self.write_attempts += 1
        return "NOT_ENABLED_IN_PHASE_1"
