import html
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

# CrossRef titles and abstracts are often JATS XML — strip all tags
_XML_TAG = re.compile(r"<[^>]+>")

# PubMed-specific query syntax that CrossRef does not understand
_PUBMED_DATE = re.compile(r"\s+AND\s+\(\d{4}:\d{4}\[PDAT\]\)", re.IGNORECASE)
_PUBMED_AFFIL = re.compile(r'\s+AND\s+"[^"]*"\[Affiliation\]', re.IGNORECASE)
_PUBMED_FIELD_TAG = re.compile(r"\[[A-Za-z ]+\]")

# Record types that represent actual publications (not journal/funder metadata)
_ARTICLE_TYPES = (
    "journal-article",
    "proceedings-article",
    "posted-content",
    "book-chapter",
    "report",
)

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

    @staticmethod
    def _clean_query(query: str) -> str:
        """Strip PubMed-specific operators that CrossRef does not understand."""
        q = _PUBMED_DATE.sub("", query)
        q = _PUBMED_AFFIL.sub("", q)
        q = _PUBMED_FIELD_TAG.sub("", q)
        return q.strip()

    def search(self, query: str, max_results: int = 20) -> List[Paper]:

        clean_query = self._clean_query(query)
        logger.info(f"Searching CrossRef: {clean_query}")

        # Request more rows than needed so that after type-filtering we still
        # return up to max_results relevant articles.
        fetch_rows = min(max_results * 3, 1000)

        # Filter to article-type records only so that journal/funder metadata
        # records (which have no authors or abstracts) are excluded.
        type_filter = ",".join(f"type:{t}" for t in _ARTICLE_TYPES)

        params: dict = {
            "query": clean_query,
            "rows": fetch_rows,
            "sort": "relevance",
            "select": _SELECT_FIELDS,
            "filter": type_filter,
        }

        if self.email:
            params["mailto"] = self.email

        headers = {"User-Agent": f"MedicalResearchAI/0.1 (mailto:{self.email})"}

        response = requests.get(_BASE_URL, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        items = response.json().get("message", {}).get("items", [])

        papers = [self._parse_item(item) for item in items[:max_results]]

        logger.info(f"CrossRef returned {len(papers)} papers")

        return papers

    def _parse_item(self, item: dict) -> Paper:

        doi = (item.get("DOI") or "").strip() or None

        title_list = item.get("title") or []
        title_raw = title_list[0] if title_list else ""
        title = html.unescape(_XML_TAG.sub("", title_raw)).strip()

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
            if date_parts and date_parts[0] and date_parts[0][0] is not None:
                try:
                    return int(date_parts[0][0])
                except (TypeError, ValueError):
                    continue
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
