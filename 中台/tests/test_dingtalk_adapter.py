"""Tests for DingTalk adapter."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.adapters.dingtalk_adapter import DingTalkAdapter
from app.models.types import CardData, CardSection, CardAction


@pytest.fixture
def adapter():
    """Create DingTalk adapter instance for testing."""
    return DingTalkAdapter(
        app_key="test_key",
        app_secret="test_secret",
        robot_code="test_robot"
    )


@pytest.mark.asyncio
async def test_send_group_card(adapter):
    """Test sending card to group."""
    card = CardData(
        title="Test Card",
        sections=[CardSection(text="Test content")],
        actions=[]
    )

    with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"cardBizId": "card_123"}
        card_id = await adapter.send_group_card("group_1", card)

        assert card_id == "card_123"
        mock_req.assert_called_once()
        call_args = mock_req.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/v1.0/card/instances"
        payload = call_args[1]['json']
        assert payload['robotCode'] == "test_robot"
        assert payload['openConversationId'] == "group_1"


@pytest.mark.asyncio
async def test_update_group_card(adapter):
    """Test updating existing group card."""
    card = CardData(
        title="Updated Card",
        sections=[CardSection(text="Updated content")],
        actions=[]
    )

    with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {}
        await adapter.update_group_card("card_123", card)

        mock_req.assert_called_once()
        call_args = mock_req.call_args
        assert call_args[0][0] == "PUT"
        assert call_args[0][1] == "/v1.0/card/instances"
        payload = call_args[1]['json']
        assert payload['cardBizId'] == "card_123"


@pytest.mark.asyncio
async def test_send_private_message(adapter):
    """Test sending private text message."""
    with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {}
        await adapter.send_private_message("user_1", "Hello, World!")

        mock_req.assert_called_once()
        call_args = mock_req.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/v1.0/robot/oToMessages/batchSend"
        payload = call_args[1]['json']
        assert payload['robotCode'] == "test_robot"


@pytest.mark.asyncio
async def test_send_private_card(adapter):
    """Test sending private card."""
    card = CardData(
        title="Private Card",
        sections=[CardSection(text="Private message")],
        actions=[]
    )

    with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {}
        await adapter.send_private_card("user_1", card)

        mock_req.assert_called_once()
        call_args = mock_req.call_args
        assert call_args[0][0] == "POST"
        payload = call_args[1]['json']
        assert payload['openConversationId'] == "user_1"


@pytest.mark.asyncio
async def test_download_file(adapter):
    """Test downloading file from message."""
    mock_file_content = b"fake file content"

    # Mock _request to return download URL
    with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"downloadUrl": "https://example.com/file.pdf"}

        # Mock _client.get to return file content
        with patch.object(adapter._client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.content = mock_file_content
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            content = await adapter.download_file("msg_123")

            assert content == mock_file_content
            mock_req.assert_called_once()
            mock_get.assert_called_once_with("https://example.com/file.pdf")


def test_card_to_dingtalk_simple(adapter):
    """Test converting simple card to DingTalk format."""
    card = CardData(
        title="Test Title",
        sections=[CardSection(text="Hello, World!")],
        actions=[]
    )

    result = adapter._card_to_dingtalk(card)

    assert result["header"]["title"] == "Test Title"
    assert result["header"]["template"] == "blue"
    assert "elements" in result
    assert len(result["elements"]) > 0
    assert "markdown" in result["elements"][0]
    assert "Hello, World!" in result["elements"][0]["markdown"]


def test_card_to_dingtalk_with_subtitle(adapter):
    """Test card with subtitle."""
    card = CardData(
        title="Title",
        subtitle="Subtitle here",
        sections=[],
        actions=[]
    )

    result = adapter._card_to_dingtalk(card)

    markdown = result["elements"][0]["markdown"]
    assert "**Subtitle here**" in markdown


def test_card_to_dingtalk_with_fields(adapter):
    """Test card with key-value fields."""
    card = CardData(
        title="Task Info",
        sections=[CardSection(fields={"Status": "Pending", "Priority": "High"})],
        actions=[]
    )

    result = adapter._card_to_dingtalk(card)

    markdown = result["elements"][0]["markdown"]
    assert "**Status**: Pending" in markdown
    assert "**Priority**: High" in markdown


def test_card_to_dingtalk_with_actions(adapter):
    """Test card with action buttons."""
    card = CardData(
        title="Action Required",
        sections=[],
        actions=[
            CardAction(label="Confirm", action="confirm"),
            CardAction(label="Cancel", action="cancel", style="danger")
        ]
    )

    result = adapter._card_to_dingtalk(card)

    assert "buttonList" in result["elements"][0]
    buttons = result["elements"][0]["buttonList"]
    assert len(buttons) == 2

    # Check first button
    assert buttons[0]["text"] == "Confirm"
    assert buttons[0]["action"] == "confirm"
    assert buttons[0]["type"] == "normal"

    # Check second button
    assert buttons[1]["text"] == "Cancel"
    assert buttons[1]["type"] == "danger"


def test_card_to_dingtalk_primary_action(adapter):
    """Test primary action style."""
    card = CardData(
        title="Primary Action",
        sections=[],
        actions=[CardAction(label="Submit", action="submit", style="primary")]
    )

    result = adapter._card_to_dingtalk(card)

    buttons = result["elements"][0]["buttonList"]
    assert buttons[0]["type"] == "primary"


def test_card_to_dingtalk_action_with_value(adapter):
    """Test action with value payload."""
    card = CardData(
        title="Action with Value",
        sections=[],
        actions=[CardAction(label="Approve", action="approve", value="task_123")]
    )

    result = adapter._card_to_dingtalk(card)

    buttons = result["elements"][0]["buttonList"]
    assert buttons[0]["value"] == "task_123"


def test_get_name(adapter):
    """Test get_name returns correct adapter name."""
    assert adapter.get_name() == "dingtalk"


@pytest.mark.asyncio
async def test_get_access_token_caching(adapter):
    """Test access token caching."""
    # Mock successful token response
    with patch.object(adapter._client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "accessToken": "test_token",
            "expireIn": 7200
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # First call should fetch token
        token1 = await adapter._get_access_token()
        assert token1 == "test_token"
        assert mock_post.call_count == 1

        # Second call should use cached token
        token2 = await adapter._get_access_token()
        assert token2 == "test_token"
        assert mock_post.call_count == 1  # No additional call


@pytest.mark.asyncio
async def test_request_retry_on_failure(adapter):
    """Test exponential backoff retry logic."""
    import httpx

    # Mock _get_access_token
    with patch.object(adapter, '_get_access_token', new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "cached_token"

        # Mock failing requests then success
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.HTTPStatusError("Server error", request=MagicMock(), response=MagicMock())
            # Return a proper mock response object
            mock_response = MagicMock()
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status = MagicMock()
            return mock_response

        with patch.object(adapter._client, 'request', new=mock_request):
            result = await adapter._request("GET", "/test")
            assert result == {"success": True}
            assert call_count == 3  # Two failures, one success
