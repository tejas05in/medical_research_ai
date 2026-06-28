from typing import List

from models import Paper
from services.base_client import BaseLiteratureClient
from services.pubmed_client import PubMedClient
from utils.logger import logger


class LiteratureSearchEngine:
    """
    Orchestrates searches across one or more literature database clients.

    Clients are registered at construction time. Results from all sources
    are merged and deduplicated by PMID then DOI before being returned.
    """

    def __init__(self, clients: List[BaseLiteratureClient] = None):

        if clients is None:
            clients = [PubMedClient()]

        self.clients = clients

    def search(self, query: str, max_results: int = 20) -> List[Paper]:

        all_papers: List[Paper] = []

        for client in self.clients:

            logger.info(f"Querying {client.source_name} for: {query}")

            try:
                papers = client.search(query=query, max_results=max_results)
                all_papers.extend(papers)
                logger.info(f"{client.source_name} returned {len(papers)} papers")

            except Exception as e:
                logger.error(f"{client.source_name} search failed: {e}", exc_info=True)

        return self._deduplicate(all_papers)

    def _deduplicate(self, papers: List[Paper]) -> List[Paper]:
        """Remove duplicates: first by PMID, then by DOI for remaining papers."""

        seen_pmids: set = set()
        seen_dois: set = set()
        unique: List[Paper] = []

        for paper in papers:

            if paper.pmid and paper.pmid in seen_pmids:
                continue

            if paper.doi and paper.doi in seen_dois:
                continue

            if paper.pmid:
                seen_pmids.add(paper.pmid)

            if paper.doi:
                seen_dois.add(paper.doi)

            unique.append(paper)

        return unique
