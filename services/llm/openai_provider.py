from typing import Type

from openai import OpenAI
from pydantic import BaseModel

from config.llm_config import OPENAI_API_KEY, OPENAI_MODEL
from .base_provider import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):

    def __init__(self):

        self.client = OpenAI(api_key=OPENAI_API_KEY)

        self.model = OPENAI_MODEL

    def structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[BaseModel],
    ) -> BaseModel:

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=schema,
        )

        return completion.choices[0].message.parsed
