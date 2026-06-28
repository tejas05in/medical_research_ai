from config.llm_config import LLM_PROVIDER
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider


class LLMService:

    def __init__(self):

        provider = LLM_PROVIDER

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
