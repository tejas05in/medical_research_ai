import os
import re
from typing import List, Optional

import requests
from dotenv import load_dotenv

from models import Paper
from services.base_client import BaseLiteratureClient
from utils.logger import logger

load_dotenv()

_BASE_URL = "https://api.crossref.org/works"

# CrossRef abstracts are often JATS XML — strip all tags
_XML_TAG = re.compile(r"<[^>]+>")

# Fields to request (reduces payload and speeds up response)
_SELECT_FIELDS = ",".join(
    [
        "DOI",
        "title",
        "author",
        "abstract",
        "published-print",
        "published-online",
        "issued",
        "container-title",
        "type",
        "subject",
    ]
)


class CrossRefClient(BaseLiteratureClient):
    """
    Client for the CrossRef REST API.

    Docs: https://github.com/CrossRef/rest-api-doc
    Auth: None required. Uses polite pool via NCBI_EMAIL in User-Agent header.
    Note: CrossRef does not provide PMIDs; pmid is always None.
    Abstract: Often wrapped in JATS XML — tags are stripped automatically.
    """

    def __init__(self):

        self.email = os.getenv("NCBI_EMAIL", "")

    @property
    def source_name(self) -> str:
        return "CrossRef"

    def search(self, query: str, max_results: int = 20) -> List[Paper]:

        logger.info(f"Searching CrossRef: {query}")

        params: dict = {
            "query": query,
            "rows": min(max_results, 1000),
            "sort": "relevance",
            "select": _SELECT_FIELDS,
        }

        if self.email:
            params["mailto"] = self.email

        headers = {"User-Agent": f"MedicalResearchAI/0.1 (mailto:{self.email})"}

        response = requests.get(_BASE_URL, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        items = response.json().get("message", {}).get("items", [])

        papers = [self._parse_item(item) for item in items]

        logger.info(f"CrossRef returned {len(papers)} papers")

        return papers

    def _parse_item(self, item: dict) -> Paper:

        doi = (item.get("DOI") or "").strip() or None

        title_list = item.get("title") or []
        title = title_list[0] if title_list else ""

        abstract_raw = item.get("abstract") or ""
        abstract = _XML_TAG.sub("", abstract_raw).strip()

        journal_list = item.get("container-title") or []
        journal = journal_list[0] if journal_list else ""

        year = self._extract_year(item)

        authors = self._parse_authors(item.get("author") or [])

        return Paper(
            source="CrossRef",
            source_id=doi,
            pmid=None,
            doi=doi,
            title=title,
            authors=authors,
            journal=journal,
            year=str(year) if year else "",
            abstract=abstract,
            keywords=item.get("subject") or [],
            mesh_terms=[],
            publication_types=[item["type"]] if item.get("type") else [],
            language="",
            url=f"https://doi.org/{doi}" if doi else "",
        )

    def _extract_year(self, item: dict) -> Optional[int]:
        """
        Try date fields in order of preference to extract the publication year.
        date-parts is a nested list: [[year, month, day]] or [[year, month]] or [[year]].
        """
        for field in ("published-print", "published-online", "issued", "published"):
            date_parts = (item.get(field) or {}).get("date-parts") or []
            if date_parts and date_parts[0]:
                return date_parts[0][0]
        return None

    def _parse_authors(self, authors: list) -> List[str]:

        result = []

        for a in authors:
            given = a.get("given", "")
            family = a.get("family", "")
            # Some entries only have a collective name
            name = (
                f"{given} {family}".strip() if (given or family) else a.get("name", "")
            )
            if name:
                result.append(name)

        return result
