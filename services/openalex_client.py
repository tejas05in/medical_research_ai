import os
from typing import List, Optional

import requests
from dotenv import load_dotenv

from models import Paper
from services.base_client import BaseLiteratureClient
from utils.logger import logger

load_dotenv()

_BASE_URL = "https://api.openalex.org/works"

# Only request fields we actually use to reduce payload size
_SELECT_FIELDS = ",".join(
    [
        "id",
        "doi",
        "title",
        "authorships",
        "publication_year",
        "abstract_inverted_index",
        "primary_location",
        "ids",
        "type",
    ]
)


class OpenAlexClient(BaseLiteratureClient):
    """
    Client for the OpenAlex REST API.

    Docs: https://docs.openalex.org/api-entities/works/search-works
    Auth: Free API key recommended (openalex.org/settings/api).
          Falls back to polite pool via NCBI_EMAIL if key not set.
    Abstract: Stored as an inverted index; reconstructed to plain text here.
    """

    def __init__(self):

        self.api_key = os.getenv("OPENALEX_API_KEY")
        self.email = os.getenv("NCBI_EMAIL", "")

        if not self.api_key and not self.email:
            logger.warning(
                "OpenAlex: neither OPENALEX_API_KEY nor NCBI_EMAIL is set. "
                "Requests may be rate-limited."
            )

    @property
    def source_name(self) -> str:
        return "OpenAlex"

    def search(self, query: str, max_results: int = 20) -> List[Paper]:

        logger.info(f"Searching OpenAlex: {query}")

        params: dict = {
            "search": query,
            "per_page": min(max_results, 200),
            "select": _SELECT_FIELDS,
        }

        if self.api_key:
            params["api_key"] = self.api_key
        elif self.email:
            params["mailto"] = self.email

        response = requests.get(_BASE_URL, params=params, timeout=30)
        response.raise_for_status()

        results = response.json().get("results", [])

        papers = [self._parse_result(r) for r in results]

        logger.info(f"OpenAlex returned {len(papers)} papers")

        return papers

    def _parse_result(self, r: dict) -> Paper:

        openalex_id = r.get("id", "")

        # DOI comes as "https://doi.org/10.xxxx" — strip prefix
        raw_doi = r.get("doi") or ""
        doi = raw_doi.replace("https://doi.org/", "").strip() or None

        # PMID comes as "https://pubmed.ncbi.nlm.nih.gov/12345678" — extract number
        ids = r.get("ids") or {}
        raw_pmid = ids.get("pmid") or ""
        pmid = (
            raw_pmid.replace("https://pubmed.ncbi.nlm.nih.gov/", "").strip("/") or None
        )

        abstract = self._reconstruct_abstract(r.get("abstract_inverted_index"))

        authors = [
            a["author"]["display_name"]
            for a in r.get("authorships", [])
            if (a.get("author") or {}).get("display_name")
        ]

        primary_location = r.get("primary_location") or {}
        source = primary_location.get("source") or {}
        journal = source.get("display_name", "")

        year = r.get("publication_year")

        return Paper(
            source="OpenAlex",
            source_id=openalex_id,
            pmid=pmid,
            doi=doi,
            title=r.get("title") or "",
            authors=authors,
            journal=journal,
            year=str(year) if year else "",
            abstract=abstract,
            keywords=[],
            mesh_terms=[],
            publication_types=[r["type"]] if r.get("type") else [],
            language="",
            url=f"https://doi.org/{doi}" if doi else openalex_id,
        )

    def _reconstruct_abstract(self, inverted_index: Optional[dict]) -> str:
        """
        Reconstruct plain-text abstract from OpenAlex inverted index format.

        The inverted index maps each word to the list of positions it appears at.
        Example: {"The": [0], "objective": [1], "of": [2, 8]}
        """
        if not inverted_index:
            return ""

        positions: List[tuple] = []

        for word, indices in inverted_index.items():
            for i in indices:
                positions.append((i, word))

        positions.sort(key=lambda x: x[0])

        return " ".join(word for _, word in positions)
