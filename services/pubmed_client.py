from Bio import Entrez
from Bio import Medline
from utils.logger import logger
import os
from dotenv import load_dotenv

from services.base_client import BaseLiteratureClient
from services.pubmed_parser import parse_medline
from models import Paper
from typing import List

load_dotenv()

Entrez.email = os.getenv("NCBI_EMAIL", "your_email@example.com")
Entrez.api_key = os.getenv("NCBI_API_KEY")


class PubMedClient(BaseLiteratureClient):

    @property
    def source_name(self) -> str:
        return "PubMed"

    def search(self, query: str, max_results: int = 20) -> List[Paper]:

        logger.info(f"Searching PubMed: {query}")

        pmids = self._search_pmids(query, max_results)

        records = self._fetch_records(pmids)

        return parse_medline(records)

    def _search_pmids(self, query: str, max_results: int):

        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)

        record = Entrez.read(handle)

        logger.info(f"Retrieved {len(record['IdList'])} PMIDs")

        return record["IdList"]

    def _fetch_records(self, pmids):

        if not pmids:
            return []

        ids = ",".join(pmids)

        handle = Entrez.efetch(db="pubmed", id=ids, rettype="medline", retmode="text")

        records = Medline.parse(handle)

        return list(records)
