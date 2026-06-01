"""Base adapter interface for all messaging platforms."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.types import CardData


class MessageAdapter(ABC):
    """Abstract base class for messaging platform adapters.

    Each platform (DingTalk, WeCom, etc.) must implement this interface
    to provide unified messaging capabilities.
    """

    @abstractmethod
    async def send_group_card(self, group_id: str, card: 'CardData') -> str:
        """Send interactive card to group, return card_id.

        Args:
            group_id: The group chat ID
            card: CardData instance with card content

        Returns:
            card_id: ID for updating the card later
        """

    @abstractmethod
    async def update_group_card(self, card_id: str, card: 'CardData') -> None:
        """Update existing interactive card.

        Args:
            card_id: The card ID returned from send_group_card
            card: New card content
        """

    @abstractmethod
    async def send_private_message(self, user_id: str, message: str) -> None:
        """Send private text message.

        Args:
            user_id: The user's ID in the platform
            message: Plain text message
        """

    @abstractmethod
    async def send_private_card(self, user_id: str, card: 'CardData') -> None:
        """Send interactive card in private chat.

        Args:
            user_id: The user's ID in the platform
            card: CardData instance with card content
        """

    @abstractmethod
    async def download_file(self, message_id: str) -> bytes:
        """Download file from message.

        Args:
            message_id: The message ID containing the file

        Returns:
            File content as bytes
        """

    @abstractmethod
    def get_name(self) -> str:
        """Return adapter name."""
        pass
