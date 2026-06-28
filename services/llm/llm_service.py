import os

from dotenv import load_dotenv

from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider

load_dotenv()


class LLMService:

    def __init__(self):

        provider = os.getenv("LLM_PROVIDER", "gemini").lower()

        providers = {
            "gemini": GeminiProvider,
            "openai": OpenAIProvider,
        }

        if provider not in providers:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        self.provider = providers[provider]()

    def structured_output(
        self,
        system_prompt,
        user_prompt,
        schema,
    ):
        return self.provider.structured_output(
            system_prompt,
            user_prompt,
            schema,
        )
