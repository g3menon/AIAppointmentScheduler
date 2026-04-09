class FakeCalendarMcp:
    def __init__(self) -> None:
        self.holds: list[dict] = []

    def create_hold(self, payload: dict) -> str:
        event_id = f"fake_event_{len(self.holds)+1}"
        self.holds.append({"event_id": event_id, **payload})
        return event_id


class FakeNotesMcp:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def append(self, line: str) -> None:
        self.lines.append(line)


class FakeEmailMcp:
    def __init__(self) -> None:
        self.drafts: list[dict] = []

    def create_draft(self, to: str, subject: str, body_markdown: str) -> str:
        draft_id = f"fake_draft_{len(self.drafts)+1}"
        self.drafts.append(
            {
                "draft_id": draft_id,
                "to": to,
                "subject": subject,
                "body_markdown": body_markdown,
            }
        )
        return draft_id

