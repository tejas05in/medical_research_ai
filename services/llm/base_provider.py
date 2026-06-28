from abc import ABC, abstractmethod
from typing import Type
from pydantic import BaseModel


class BaseLLMProvider(ABC):

    @abstractmethod
    def structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[BaseModel],
    ) -> BaseModel:
        """
        Generate a structured response validated
        against the supplied Pydantic schema.
        """
        raise NotImplementedError
