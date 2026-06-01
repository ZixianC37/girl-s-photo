"""DingTalk adapter implementation."""

import asyncio
import time
from typing import Dict, Any, Optional

import httpx

from app.adapters.base import MessageAdapter
from app.models.types import CardData, CardSection, CardAction


class DingTalkAdapter(MessageAdapter):
    """DingTalk messaging platform adapter.

    Implements DingTalk Open Platform API:
    - OAuth2 token management
    - Interactive card sending/updating
    - Private message sending
    - File download
    """

    DINGTALK_API_BASE = "https://api.dingtalk.com"

    def __init__(self, app_key: str, app_secret: str, robot_code: str):
        """Initialize DingTalk adapter.

        Args:
            app_key: DingTalk app key
            app_secret: DingTalk app secret
            robot_code: DingTalk robot code
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.robot_code = robot_code
        self._access_token: Optional[str] = None
        self._token_expires: int = 0  # Unix timestamp
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _get_access_token(self) -> str:
        """Get or refresh access token.

        Token is cached until expiry (typically 2 hours).

        Returns:
            Valid access token
        """
        now = int(time.time())

        # Return cached token if still valid (with 5min buffer)
        if self._access_token and self._token_expires > now + 300:
            return self._access_token

        # Fetch new token
        url = f"{self.DINGTALK_API_BASE}/v1.0/oauth2/accessToken"
        response = await self._client.post(
            url,
            json={
                "appKey": self.app_key,
                "appSecret": self.app_secret
            }
        )
        response.raise_for_status()
        data = response.json()

        self._access_token = data["accessToken"]
        self._token_expires = now + data.get("expireIn", 7200)

        return self._access_token

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Make authenticated API request with retry.

        Implements exponential backoff: 1s, 2s, 4s (max 3 retries).

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g., /v1.0/card/instances)
            **kwargs: Additional arguments for httpx

        Returns:
            Response JSON as dict
        """
        url = f"{self.DINGTALK_API_BASE}{path}"
        max_retries = 3
        base_delay = 1.0  # seconds

        for attempt in range(max_retries):
            try:
                token = await self._get_access_token()
                headers = kwargs.pop('headers', {})
                headers["Authorization"] = f"Bearer {token}"

                response = await self._client.request(
                    method,
                    url,
                    headers=headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()

            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)

        # Should never reach here
        raise RuntimeError("Request failed after all retries")

    def _card_to_dingtalk(self, card: CardData) -> Dict[str, Any]:
        """Convert CardData to DingTalk card JSON format.

        DingTalk card structure:
        {
            "header": {"title": "...", "template": "blue"},
            "elements": [
                {"markdown": "..."},
                {"button": {"text": "...", "type": "primary"}}
            ]
        }

        Args:
            card: CardData instance

        Returns:
            DingTalk card JSON
        """
        elements: Dict[str, Any] = {}

        # Build markdown content from sections
        markdown_lines = []
        if card.subtitle:
            markdown_lines.append(f"**{card.subtitle}**")

        for section in card.sections:
            if section.text:
                markdown_lines.append(section.text)

            if section.fields:
                for key, value in section.fields.items():
                    markdown_lines.append(f"**{key}**: {value}")

        if markdown_lines:
            elements["markdown"] = "\n\n".join(markdown_lines)

        # Convert actions to buttons
        if card.actions:
            buttons = []
            for action in card.actions:
                button: Dict[str, Any] = {"text": action.label}
                if action.style == "primary":
                    button["type"] = "primary"
                elif action.style == "danger":
                    button["type"] = "danger"
                else:
                    button["type"] = "normal"

                # Store action identifier and optional value
                button["action"] = action.action
                if action.value:
                    button["value"] = action.value

                buttons.append(button)

            if buttons:
                elements["buttonList"] = buttons

        # Build final card
        dingtalk_card = {
            "header": {
                "title": card.title,
                "template": "blue"  # Default color
            }
        }

        if elements:
            dingtalk_card["elements"] = [elements]

        return dingtalk_card

    async def send_group_card(self, group_id: str, card: CardData) -> str:
        """Send interactive card to group.

        Args:
            group_id: DingTalk group chat ID
            card: CardData instance

        Returns:
            cardBizId for updating the card later
        """
        dingtalk_card = self._card_to_dingtalk(card)

        payload = {
            "robotCode": self.robot_code,
            "openConversationId": group_id,
            "cardData": dingtalk_card,
            "msg": f"【{card.title}】"  # Fallback text notification
        }

        response = await self._request(
            "POST",
            "/v1.0/card/instances",
            json=payload
        )

        return response.get("cardBizId", "")

    async def update_group_card(self, card_id: str, card: CardData) -> None:
        """Update existing interactive card.

        Args:
            card_id: cardBizId from send_group_card
            card: New CardData content
        """
        dingtalk_card = self._card_to_dingtalk(card)

        payload = {
            "robotCode": self.robot_code,
            "cardBizId": card_id,
            "cardData": dingtalk_card
        }

        await self._request(
            "PUT",
            "/v1.0/card/instances",
            json=payload
        )

    async def send_private_message(self, user_id: str, message: str) -> None:
        """Send private text message.

        Args:
            user_id: DingTalk user ID (unionId or staffId)
            message: Plain text message
        """
        payload = {
            "robotCode": self.robot_code,
            "msgKeys": ["sample_text"],  # Message template key
            "msgParam": f'{{"text": "{message}"}}',
            "openConversationId": user_id,  # For private message
            "aggregate": False
        }

        await self._request(
            "POST",
            "/v1.0/robot/oToMessages/batchSend",
            json=payload
        )

    async def send_private_card(self, user_id: str, card: CardData) -> None:
        """Send interactive card in private chat.

        Args:
            user_id: DingTalk user ID
            card: CardData instance
        """
        dingtalk_card = self._card_to_dingtalk(card)

        payload = {
            "robotCode": self.robot_code,
            "openConversationId": user_id,  # Private conversation
            "cardData": dingtalk_card,
            "msg": f"【{card.title}】"  # Fallback text notification
        }

        await self._request(
            "POST",
            "/v1.0/card/instances",
            json=payload
        )

    async def download_file(self, message_id: str) -> bytes:
        """Download file from message.

        Args:
            message_id: DingTalk message ID containing file

        Returns:
            File content as bytes
        """
        payload = {
            "robotCode": self.robot_code,
            "msgId": message_id
        }

        response = await self._request(
            "POST",
            "/v1.0/robot/messageFiles/download",
            json=payload
        )

        # Response typically contains download URL
        download_url = response.get("downloadUrl")
        if not download_url:
            raise ValueError("No download URL in response")

        # Download actual file content
        file_response = await self._client.get(download_url)
        file_response.raise_for_status()

        return file_response.content

    def get_name(self) -> str:
        """Return adapter name."""
        return "dingtalk"

    async def send_private_text(self, user_id: str, text: str) -> None:
        """Send plain text private message (convenience wrapper)."""
        await self.send_private_message(user_id, text)

    async def close(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()
