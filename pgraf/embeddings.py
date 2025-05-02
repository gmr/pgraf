import openai


class Embeddings:
    def __init__(self, openai_api_key: str | None = None) -> None:
        self.openai_client = openai.AsyncClient(api_key=openai_api_key)

    async def get(self, text: str) -> list[float]:
        """Get embeddings using OpenAI API."""
        response = await self.openai_client.embeddings.create(
            input=text, model='text-embedding-3-small'
        )
        return response.data[0].embedding
