from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class Paper:

    pmid: str
    doi: Optional[str]

    title: str

    authors: List[str]

    journal: str

    year: str

    abstract: str

    keywords: List[str] = None

    mesh_terms: List[str] = None

    publication_types: List[str] = None

    language: str = "English"

    def to_dict(self):
        return asdict(self)

    @property
    def author_string(self):
        return ", ".join(self.authors)
