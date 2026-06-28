from typing import Type

from google import genai
from pydantic import BaseModel

from config.llm_config import GEMINI_API_KEY, GEMINI_MODEL
from .base_provider import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):

    def __init__(self):

        self.client = genai.Client(api_key=GEMINI_API_KEY)

        self.model = GEMINI_MODEL

    def structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[BaseModel],
    ) -> BaseModel:

        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config={
                "system_instruction": system_prompt,
                "response_mime_type": "application/json",
                "response_schema": schema,
                "temperature": 0,
            },
        )

        return schema.model_validate_json(response.text)
