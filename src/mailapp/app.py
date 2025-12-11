from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from mailapp.widgets.email_list import EmailList
from mailapp.widgets.sidebar import Sidebar


class MailApp(App):
    """A Textual app to manage emails."""

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Sidebar()
        yield EmailList()
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )
