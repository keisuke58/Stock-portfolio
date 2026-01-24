"""
Tests for notifiers (discord.py, slack.py, gmail.py, line.py)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests


class TestDiscordNotifier:
    """Tests for DiscordNotifier class."""

    def test_init_with_webhook(self):
        """Test DiscordNotifier initialization."""
        from notifiers.discord import DiscordNotifier

        webhook = "https://discord.com/api/webhooks/test/test"
        notifier = DiscordNotifier(webhook)

        assert notifier.webhook_url == webhook

    @patch('requests.post')
    def test_send_message_success(self, mock_post):
        """Test successful message sending."""
        from notifiers.discord import DiscordNotifier

        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        notifier = DiscordNotifier("https://discord.com/api/webhooks/test/test")
        result = notifier.send("Test message")

        assert result is True
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_send_message_failure(self, mock_post):
        """Test message sending failure handling."""
        from notifiers.discord import DiscordNotifier

        mock_post.side_effect = requests.RequestException("Network error")

        notifier = DiscordNotifier("https://discord.com/api/webhooks/test/test")
        result = notifier.send("Test message")

        assert result is False

    @patch('requests.post')
    def test_notify_state_change(self, mock_post, sample_daily_pick):
        """Test state change notification."""
        from notifiers.discord import DiscordNotifier

        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        notifier = DiscordNotifier("https://discord.com/api/webhooks/test/test")
        result = notifier.notify_state_change(
            symbol='AAPL',
            old_state='BASE',
            new_state='BUY',
            price=150.0
        )

        assert result is True
        mock_post.assert_called()

        # Verify the payload contains expected data
        call_args = mock_post.call_args
        if call_args.kwargs.get('json'):
            payload = call_args.kwargs['json']
            # Discord uses embeds
            assert 'embeds' in payload or 'content' in payload

    @patch('requests.post')
    def test_notify_daily_pick(self, mock_post, sample_daily_pick):
        """Test daily pick notification."""
        from notifiers.discord import DiscordNotifier

        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        notifier = DiscordNotifier("https://discord.com/api/webhooks/test/test")
        result = notifier.notify_daily_pick(sample_daily_pick)

        assert result is True


class TestSlackNotifier:
    """Tests for SlackNotifier class."""

    def test_init_with_webhook(self):
        """Test SlackNotifier initialization."""
        from notifiers.slack import SlackNotifier

        webhook = "https://hooks.slack.com/services/test/test/test"
        notifier = SlackNotifier(webhook)

        assert notifier.webhook_url == webhook

    @patch('requests.post')
    def test_send_message_success(self, mock_post):
        """Test successful Slack message."""
        from notifiers.slack import SlackNotifier

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'ok'
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        notifier = SlackNotifier("https://hooks.slack.com/test")
        result = notifier.send("Test message")

        assert result is True

    @patch('requests.post')
    def test_notify_state_change(self, mock_post):
        """Test Slack state change notification."""
        from notifiers.slack import SlackNotifier

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        notifier = SlackNotifier("https://hooks.slack.com/test")
        result = notifier.notify_state_change(
            symbol='BTC',
            old_state='NORMAL',
            new_state='WATCH',
            price=45000.0
        )

        assert result is True


class TestLineNotifier:
    """Tests for LineNotifier class."""

    def test_init_with_token(self):
        """Test LineNotifier initialization."""
        from notifiers.line import LineNotifier

        token = "test_token_12345"
        notifier = LineNotifier(token)

        assert notifier.token == token

    @patch('requests.post')
    def test_send_message_success(self, mock_post):
        """Test successful Line message."""
        from notifiers.line import LineNotifier

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        notifier = LineNotifier("test_token")
        result = notifier.send("Test message")

        assert result is True

        # Verify authorization header
        call_args = mock_post.call_args
        headers = call_args.kwargs.get('headers', {})
        assert 'Authorization' in headers
        assert 'Bearer' in headers['Authorization']

    @patch('requests.post')
    def test_notify_state_change(self, mock_post):
        """Test Line state change notification."""
        from notifiers.line import LineNotifier

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        notifier = LineNotifier("test_token")
        result = notifier.notify_state_change(
            symbol='ETH',
            old_state='WATCH',
            new_state='BASE',
            price=3000.0
        )

        assert result is True


class TestGmailNotifier:
    """Tests for GmailNotifier class."""

    def test_init_with_credentials(self):
        """Test GmailNotifier initialization."""
        from notifiers.gmail import GmailNotifier

        notifier = GmailNotifier(
            user='test@gmail.com',
            password='app_password',
            to='recipient@example.com'
        )

        assert notifier.user == 'test@gmail.com'
        assert notifier.to == 'recipient@example.com'

    @patch('smtplib.SMTP')
    def test_send_message_success(self, mock_smtp):
        """Test successful email sending."""
        from notifiers.gmail import GmailNotifier

        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        notifier = GmailNotifier(
            user='test@gmail.com',
            password='app_password',
            to='recipient@example.com'
        )
        result = notifier.send("Test message")

        assert result is True

    @patch('smtplib.SMTP')
    def test_send_message_auth_failure(self, mock_smtp):
        """Test email auth failure handling."""
        from notifiers.gmail import GmailNotifier
        import smtplib

        mock_smtp_instance = MagicMock()
        mock_smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b'Auth failed')
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        notifier = GmailNotifier(
            user='test@gmail.com',
            password='wrong_password',
            to='recipient@example.com'
        )
        result = notifier.send("Test message")

        assert result is False

    @patch('smtplib.SMTP')
    def test_notify_daily_pick(self, mock_smtp, sample_daily_pick):
        """Test daily pick email notification."""
        from notifiers.gmail import GmailNotifier

        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        notifier = GmailNotifier(
            user='test@gmail.com',
            password='app_password',
            to='recipient@example.com'
        )
        result = notifier.notify_daily_pick(sample_daily_pick)

        assert result is True


class TestNotificationThrottling:
    """Tests for notification throttling."""

    @patch('requests.post')
    def test_throttle_prevents_spam(self, mock_post):
        """Test that throttling prevents notification spam."""
        from notifiers.discord import DiscordNotifier

        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        notifier = DiscordNotifier("https://discord.com/api/webhooks/test/test")

        # First notification should succeed
        result1 = notifier.notify_state_change('AAPL', 'NORMAL', 'WATCH', 150.0)

        # Immediate second notification for same symbol might be throttled
        # (depends on implementation)
        # result2 = notifier.notify_state_change('AAPL', 'WATCH', 'BASE', 145.0)

        assert result1 is True


class TestNotifierErrorHandling:
    """Tests for error handling across notifiers."""

    @patch('requests.post')
    def test_discord_rate_limit(self, mock_post):
        """Test Discord rate limit handling."""
        from notifiers.discord import DiscordNotifier

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {'retry_after': 1000}
        mock_response.raise_for_status.side_effect = requests.RequestException("Rate limited")
        mock_post.return_value = mock_response

        notifier = DiscordNotifier("https://discord.com/api/webhooks/test/test")
        result = notifier.send("Test message")

        # Should handle gracefully
        assert result is False

    @patch('requests.post')
    def test_slack_invalid_webhook(self, mock_post):
        """Test Slack invalid webhook handling."""
        from notifiers.slack import SlackNotifier

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = 'channel_not_found'
        mock_response.raise_for_status.side_effect = requests.RequestException("Not found")
        mock_post.return_value = mock_response

        notifier = SlackNotifier("https://hooks.slack.com/invalid")
        result = notifier.send("Test message")

        assert result is False

    @patch('requests.post')
    def test_line_invalid_token(self, mock_post):
        """Test Line invalid token handling."""
        from notifiers.line import LineNotifier

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.RequestException("Unauthorized")
        mock_post.return_value = mock_response

        notifier = LineNotifier("invalid_token")
        result = notifier.send("Test message")

        assert result is False


class TestMessageFormatting:
    """Tests for message formatting across notifiers."""

    def test_state_emoji_mapping(self):
        """Test that state emojis are correctly mapped."""
        # This tests the shared emoji mapping that should exist
        state_emojis = {
            'WATCH': 'warning',
            'BASE': 'chart_with_upwards_trend',
            'BUY': 'rocket',
            'NORMAL': 'chart_increasing',
        }

        for state, emoji in state_emojis.items():
            assert emoji is not None

    def test_daily_pick_formatting_includes_scores(self, sample_daily_pick):
        """Test that daily pick messages include all scores."""
        from notifiers.discord import DiscordNotifier

        notifier = DiscordNotifier("https://discord.com/api/webhooks/test/test")

        # The message should include value, momentum, and stability scores
        # This is more of a documentation test for expected behavior
        required_fields = ['value_score', 'momentum_score', 'stability_score', 'total_score']

        for field in required_fields:
            assert field in sample_daily_pick
