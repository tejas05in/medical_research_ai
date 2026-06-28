import os
from typing import List

import requests
from dotenv import load_dotenv

from models import Paper
from services.base_client import BaseLiteratureClient
from utils.logger import logger

load_dotenv()

_BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


class EuropePMCClient(BaseLiteratureClient):
    """
    Client for the Europe PMC REST API.

    Docs: https://europepmc.org/RestfulWebService
    Auth: none required
    Max page size: 1000; resultType=core required for full abstract.
    """

    @property
    def source_name(self) -> str:
        return "EuropePMC"

    def search(self, query: str, max_results: int = 20) -> List[Paper]:

        logger.info(f"Searching Europe PMC: {query}")

        params = {
            "query": query,
            "format": "json",
            "pageSize": min(max_results, 1000),
            "resultType": "core",
            "cursorMark": "*",
        }

        response = requests.get(_BASE_URL, params=params, timeout=30)
        response.raise_for_status()

        results = response.json().get("resultList", {}).get("result", [])

        papers = [self._parse_result(r) for r in results]

        logger.info(f"Europe PMC returned {len(papers)} papers")

        return papers

    def _parse_result(self, r: dict) -> Paper:

        return Paper(
            source="EuropePMC",
            source_id=r.get("id"),
            pmid=r.get("pmid") or None,
            doi=r.get("doi") or None,
            title=(r.get("title") or "").rstrip("."),
            authors=self._parse_authors(r),
            journal=r.get("journalTitle", ""),
            year=str(r.get("pubYear", ""))[:4],
            abstract=r.get("abstractText") or r.get("abstract") or "",
            keywords=[],
            mesh_terms=[],
            publication_types=[r["pubType"]] if r.get("pubType") else [],
            language=r.get("language", "eng"),
            url=(
                f"https://europepmc.org/article/"
                f"{r.get('source', 'MED')}/{r.get('id', '')}"
            ),
        )

    def _parse_authors(self, r: dict) -> List[str]:

        # Prefer structured author list
        author_list = r.get("authorList", {}).get("author", [])

        if author_list:
            names = []
            for a in author_list:
                name = (
                    a.get("fullName")
                    or f"{a.get('lastName', '')} {a.get('initials', '')}".strip()
                )
                if name:
                    names.append(name)
            return names

        # Fall back to comma-separated authorString
        author_str = r.get("authorString", "")
        if author_str:
            return [a.strip() for a in author_str.split(",") if a.strip()]

        return []
