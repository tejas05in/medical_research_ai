from typing import List

from models import Paper

from services.pubmed_client import PubMedClient
from services.pubmed_parser import parse_medline


class LiteratureSearchEngine:

    def __init__(self):
        self.pubmed = PubMedClient()

    def search(self, query: str, max_results: int = 20) -> List[Paper]:

        pmids = self.pubmed.search(query=query, max_results=max_results)

        records = self.pubmed.fetch(pmids)

        papers = parse_medline(records)

        return papers
