from textual.containers import ScrollableContainer

from .compact_email import CompactEmail, EmailData


class EmailList(ScrollableContainer):
    """A scrollable list of compact email widgets."""

    DEFAULT_CSS = """
    EmailList {
        width: 1fr;
        height: 1fr;
        border: solid $primary;
        layout: vertical;
    }

    EmailList > CompactEmail {
        margin: 0 0;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.emails: List[EmailData] = []

    def add_email(self, email: EmailData) -> None:
        """Add an email to the list."""
        self.emails.append(email)
        email_widget = CompactEmail(email)
        self.mount(email_widget)

    def add_emails(self, emails: List[EmailData]) -> None:
        """Add multiple emails to the list."""
        for email in emails:
            self.add_email(email)

    def clear_emails(self) -> None:
        """Clear all emails from the list."""
        self.emails.clear()
        self.query("CompactEmail").remove()

    def remove_email(self, email_id: str) -> None:
        """Remove an email by id."""
        self.emails = [e for e in self.emails if e.id != email_id]
        email_widgets = self.query(f"CompactEmail[id='{email_id}']")
        email_widgets.remove()
