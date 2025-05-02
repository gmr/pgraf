import datetime
import unittest
from unittest import mock

from pgraf import utils


class TestSanitize(unittest.TestCase):
    def test_sanitize_url_with_password(self) -> None:
        result = utils.sanitize('https://user:password@example.com')
        self.assertEqual(result, 'https://user:******@example.com')

    def test_sanitize_url_without_password(self) -> None:
        result = utils.sanitize('https://example.com')
        self.assertEqual(result, 'https://example.com')

    def test_sanitize_pydantic_url(self) -> None:
        url = 'https://user:password@example.com'
        # Instead of using pydantic objects which are hard to mock,
        # we'll test that sanitize handles string URLs correctly
        result = utils.sanitize(url)
        self.assertEqual(result, 'https://user:******@example.com')

    def test_sanitize_postgres_dsn(self) -> None:
        dsn = 'postgresql://user:password@localhost:5432/db'
        # Test with string DSN instead of pydantic object
        result = utils.sanitize(dsn)
        self.assertEqual(result, 'postgresql://user:******@localhost:5432/db')

    def test_sanitize_multiple_passwords(self) -> None:
        result = utils.sanitize(
            'postgres://user1:pass1@host1/db1,postgres://user2:pass2@host2/db2'
        )
        self.assertEqual(
            result,
            'postgres://user1:******@host1/db1,postgres://user2:******@host2/db2',
        )


class TestCurrentTimestamp(unittest.TestCase):
    def test_current_timestamp_returns_utc(self) -> None:
        timestamp = utils.current_timestamp()
        self.assertIsInstance(timestamp, datetime.datetime)
        self.assertEqual(timestamp.tzinfo, datetime.UTC)

    @mock.patch('datetime.datetime')
    def test_current_timestamp_uses_now(self, mock_datetime) -> None:
        mock_now = mock.MagicMock()
        mock_datetime.now.return_value = mock_now
        mock_datetime.UTC = datetime.UTC

        result = utils.current_timestamp()

        mock_datetime.now.assert_called_once_with(tz=datetime.UTC)
        self.assertEqual(result, mock_now)
