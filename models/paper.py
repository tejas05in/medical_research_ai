from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Paper:
    """
    Represents a biomedical publication from any literature source.

    Examples of sources:
    - PubMed
    - Europe PMC
    - OpenAlex
    - CrossRef
    - Scopus
    - Embase
    """

    # Internal database ID
    id: Optional[int] = None

    # Literature source
    source: str = "PubMed"

    # ID assigned by that source
    source_id: Optional[str] = None

    # Biomedical identifiers
    pmid: Optional[str] = None
    doi: Optional[str] = None

    # Bibliographic metadata
    title: str = ""

    authors: list[str] = field(default_factory=list)

    journal: str = ""

    year: str = ""

    abstract: str = ""

    # Metadata
    keywords: list[str] = field(default_factory=list)

    mesh_terms: list[str] = field(default_factory=list)

    publication_types: list[str] = field(default_factory=list)

    language: str = "English"

    url: Optional[str] = None

    retrieved_at: Optional[str] = None

    def to_dict(self):
        return asdict(self)

    @property
    def author_string(self):
        return ", ".join(self.authors)

    def __str__(self):
        return f"[{self.source}] " f"{self.title} " f"({self.year})"
