from textual.widgets import Static
from textual.reactive import reactive
from dataclasses import dataclass
from typing import Optional


@dataclass
class EmailData:
    """Data structure for an email."""
    id: str
    sender: str
    subject: str
    preview: str
    timestamp: str
    unread: bool = False


class CompactEmail(Static):
    """A compact email widget for displaying in a list."""

    DEFAULT_CSS = """
    CompactEmail {
        height: 3;
        border: solid $primary 0%;
        padding: 0 1;
    }

    CompactEmail:hover {
        background: $boost;
        border: solid $accent 100%;
    }

    CompactEmail.unread {
        background: $panel;
    }

    .sender {
        color: $text;
        text-style: bold;
        width: 1fr;
    }

    .timestamp {
        color: $text-muted;
        width: auto;
    }

    .subject {
        color: $text;
        width: 1fr;
        text-style: bold;
    }

    .preview {
        color: $text-muted;
        width: 1fr;
        height: 1;
        overflow: hidden;
    }
    """

    email: reactive[Optional[EmailData]] = reactive(None, init=False)

    def __init__(self, email: EmailData, **kwargs):
        super().__init__(**kwargs)
        self.email = email

    def render(self) -> str:
        if not self.email:
            return ""

        sender = self.email.sender[:20].ljust(20)
        timestamp = self.email.timestamp.rjust(10)
        subject = self.email.subject[:60]
        preview = self.email.preview[:80].replace("\n", " ")

        result = f"{sender} {timestamp}\n"
        result += f"{subject}\n"
        result += f"{preview}"

        return result

    def watch_email(self) -> None:
        """Update styles when email changes."""
        if self.email.unread:
            self.add_class("unread")
        else:
            self.remove_class("unread")
        self.refresh()
