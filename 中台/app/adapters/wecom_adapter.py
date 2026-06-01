"""WeCom (企业微信) adapter stub implementation."""

from typing import TYPE_CHECKING

from app.adapters.base import MessageAdapter

if TYPE_CHECKING:
    from app.models.types import CardData


class WeComAdapter(MessageAdapter):
    """WeCom messaging platform adapter (stub).

    TODO: Implement WeCom Open Platform API integration
    """

    async def send_group_card(self, group_id: str, card: 'CardData') -> str:
        """Send interactive card to group.

        Not yet implemented for WeCom.
        """
        raise NotImplementedError("WeCom adapter not yet implemented")

    async def update_group_card(self, card_id: str, card: 'CardData') -> None:
        """Update existing interactive card.

        Not yet implemented for WeCom.
        """
        raise NotImplementedError("WeCom adapter not yet implemented")

    async def send_private_message(self, user_id: str, message: str) -> None:
        """Send private text message.

        Not yet implemented for WeCom.
        """
        raise NotImplementedError("WeCom adapter not yet implemented")

    async def send_private_card(self, user_id: str, card: 'CardData') -> None:
        """Send interactive card in private chat.

        Not yet implemented for WeCom.
        """
        raise NotImplementedError("WeCom adapter not yet implemented")

    async def download_file(self, message_id: str) -> bytes:
        """Download file from message.

        Not yet implemented for WeCom.
        """
        raise NotImplementedError("WeCom adapter not yet implemented")

    def get_name(self) -> str:
        """Return adapter name."""
        return "wecom"
