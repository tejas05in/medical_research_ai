import os
from typing import Type

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from .base_provider import BaseLLMProvider

load_dotenv()


class OpenAIProvider(BaseLLMProvider):

    def __init__(self):

        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1")

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
