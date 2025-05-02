import unittest
from unittest import mock

from pgraf import embeddings
from tests import common


class TestEmbeddings(unittest.IsolatedAsyncioTestCase):
    @mock.patch('openai.AsyncClient')
    async def test_get_embeddings_success(
        self, mock_client: mock.MagicMock
    ) -> None:
        mock_data = mock.MagicMock()
        mock_data.embedding = common.test_embeddings()
        mock_response = mock.AsyncMock()
        mock_response.data = [mock_data]
        mock_instance = mock_client.return_value
        mock_instance.embeddings = mock.AsyncMock()
        mock_instance.embeddings.create = mock.AsyncMock(
            return_value=mock_response
        )
        instance = embeddings.Embeddings()
        result = await instance.get('test text')
        self.assertListEqual(result, mock_data.embedding)
