from abc import ABC, abstractmethod
from typing import List

from models import Paper


class BaseLiteratureClient(ABC):
    """
    Abstract base class for all literature database clients.

    Each client represents one external source (PubMed, Europe PMC, etc.)
    and must implement the search() method returning a list of Paper objects.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name of the database (e.g. 'PubMed')."""
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, max_results: int = 20) -> List[Paper]:
        """
        Search the database and return a list of Paper objects.

        Args:
            query: Search query string (Boolean operators supported).
            max_results: Maximum number of results to retrieve.

        Returns:
            List of Paper objects from this source.
        """
        raise NotImplementedError
