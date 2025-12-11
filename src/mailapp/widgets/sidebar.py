from textual.widgets import Static, Tree
from textual.widgets.tree import TreeNode
from textual.containers import Container, ScrollableContainer
from dataclasses import dataclass
from typing import Optional


@dataclass
class AccountFolder:
    """Represents a folder within an account."""
    name: str
    unread_count: int = 0
    folder_type: str = "custom"  # inbox, sent, drafts, trash, custom


@dataclass
class Account:
    """Represents an email account."""
    name: str
    email: str
    folders: list[AccountFolder]


class Sidebar(ScrollableContainer):
    """A sidebar widget showing accounts and their folders."""

    DEFAULT_CSS = """
    Sidebar {
        width: 30;
        height: 1fr;
        border: solid $primary;
        background: $panel;
    }

    Sidebar > Tree {
        width: 100%;
        height: 100%;
    }

    .folder-inbox {
        color: $primary;
        text-style: bold;
    }

    .folder-sent {
        color: $success;
    }

    .folder-drafts {
        color: $warning;
    }

    .folder-trash {
        color: $error;
    }

    .folder-custom {
        color: $text;
    }

    .unread-badge {
        color: $error;
        text-style: bold;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.accounts: list[Account] = []
        self.tree = Tree("📧 Accounts")
        self.tree.show_root = True

    def on_mount(self) -> None:
        """Mount the tree widget."""
        self.mount(self.tree)

    def add_account(self, account: Account) -> TreeNode:
        """Add an account to the sidebar."""
        self.accounts.append(account)
        account_node = self.tree.root.add(
            f"👤 {account.email}",
            expand=True,
            data=account
        )

        for folder in account.folders:
            self._add_folder(account_node, folder)

        return account_node

    def _add_folder(self, parent: TreeNode, folder: AccountFolder) -> TreeNode:
        """Add a folder to the tree."""
        unread_text = ""
        if folder.unread_count > 0:
            unread_text = f" ({folder.unread_count})"

        folder_icons = {
            "inbox": "📥",
            "sent": "📤",
            "drafts": "✏️",
            "trash": "🗑️",
            "custom": "📁",
        }

        icon = folder_icons.get(folder.folder_type, "📁")
        label = f"{icon} {folder.name}{unread_text}"

        folder_node = parent.add_leaf(label, data=folder)
        return folder_node

    def add_folder_to_account(self, account_email: str, folder: AccountFolder) -> None:
        """Add a folder to an existing account."""
        for node in self.tree.root.children:
            if hasattr(node, "data") and isinstance(node.data, Account):
                if node.data.email == account_email:
                    folder.folders.append(folder)
                    self._add_folder(node, folder)
                    return

    def update_unread_count(self, account_email: str, folder_name: str, count: int) -> None:
        """Update the unread count for a folder."""
        for account_node in self.tree.root.children:
            if hasattr(account_node, "data") and isinstance(account_node.data, Account):
                if account_node.data.email == account_email:
                    for folder_node in account_node.children:
                        if hasattr(folder_node, "data") and isinstance(folder_node.data, AccountFolder):
                            if folder_node.data.name == folder_name:
                                folder_node.data.unread_count = count
                                self._update_folder_label(folder_node)
                                return

    def _update_folder_label(self, folder_node: TreeNode) -> None:
        """Update the label of a folder node."""
        folder = folder_node.data
        unread_text = ""
        if folder.unread_count > 0:
            unread_text = f" ({folder.unread_count})"

        folder_icons = {
            "inbox": "📥",
            "sent": "📤",
            "drafts": "✏️",
            "trash": "🗑️",
            "custom": "📁",
        }

        icon = folder_icons.get(folder.folder_type, "📁")
        folder_node.label = f"{icon} {folder.name}{unread_text}"

    def get_selected_folder(self) -> Optional[AccountFolder]:
        """Get the currently selected folder."""
        selected = self.tree.cursor_node
        if selected and hasattr(selected, "data") and isinstance(selected.data, AccountFolder):
            return selected.data
        return None

    def get_selected_account(self) -> Optional[Account]:
        """Get the currently selected account."""
        selected = self.tree.cursor_node
        if selected and hasattr(selected, "data") and isinstance(selected.data, Account):
            return selected.data
        return None
