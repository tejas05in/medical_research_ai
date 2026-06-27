from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

from services.literature_engine import LiteratureSearchEngine
from database import ResearchDatabase
from utils.exporters import PaperExporter


class LiteratureSearchInput(BaseModel):
    query: str = Field(..., description="Medical literature search query")

    max_results: int = Field(default=20, description="Maximum number of papers")


class LiteratureSearchTool(BaseTool):
    name: str = "Literature Search Tool"

    description: str = (
        "Searches PubMed for biomedical literature, "
        "stores papers in the local research library, "
        "and exports CSV/Markdown/JSON."
    )

    args_schema: Type[BaseModel] = LiteratureSearchInput

    def _run(self, query: str, max_results: int = 20) -> str:

        engine = LiteratureSearchEngine()

        db = ResearchDatabase()

        exporter = PaperExporter()

        papers = engine.search(query=query, max_results=max_results)

        db.insert_many(papers)

        db.log_search(
            query=query, database_name="PubMed", number_of_results=len(papers)
        )

        csv_file = exporter.export_csv(papers)

        md_file = exporter.export_markdown(papers)

        json_file = exporter.export_json(papers)

        return f"""
                Search completed successfully.

                Query:
                {query}

                Articles Retrieved:
                {len(papers)}

                CSV:
                {csv_file}

                Markdown:
                {md_file}

                JSON:
                {json_file}
                """
