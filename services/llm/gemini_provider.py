import os
from typing import Type

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

from .base_provider import BaseLLMProvider

load_dotenv()


class GeminiProvider(BaseLLMProvider):

    def __init__(self):

        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

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
