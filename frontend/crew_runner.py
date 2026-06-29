"""
Programmatic CrewAI crew definition for Streamlit integration.

Mirrors crew.jsonc + agents/medical_literature_search_spec.jsonc via the
Python API so the crew can be invoked from code rather than the CLI only.
"""

import sys
from pathlib import Path

from crewai import Agent, Crew, Process, Task
from dotenv import load_dotenv

from config.llm_config import AGENT_SEARCH_LLM
from tools.literature_search_tool import LiteratureSearchTool

# Ensure project root is on sys.path so tool/service imports resolve correctly.
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")


def run_literature_search_crew(research_topic: str, max_results: int = 20) -> str:
    """
    Run the medical literature search crew programmatically.

    Args:
        research_topic: The enriched search query (may include date / affiliation
                        filters already embedded in the string).
        max_results:    Maximum number of papers to retrieve per database.

    Returns:
        The crew's final output string.
    """
    tool = LiteratureSearchTool()

    agent = Agent(
        role="Medical Literature Search Specialist",
        goal=(
            "Retrieve comprehensive, accurate, and up-to-date biomedical literature "
            "from PubMed, Europe PMC, OpenAlex, and CrossRef based on the user's "
            "research topic and search criteria. Construct precise Boolean search "
            "strategies, identify relevant MeSH terms, and retrieve peer-reviewed "
            "publications from all available sources, deduplicating results by PMID "
            "and DOI."
        ),
        backstory=(
            "You are an experienced medical information specialist and research "
            "librarian with expertise in systematic literature searching. You are "
            "skilled in constructing Boolean search strategies, identifying MeSH "
            "terms, retrieving peer-reviewed publications, and ensuring that no "
            "relevant studies are overlooked. You always prioritize high-quality "
            "evidence and produce structured, reproducible search results suitable "
            "for academic and clinical research."
        ),
        tools=[tool],
        llm=AGENT_SEARCH_LLM,
        verbose=True,
    )

    task = Task(
        description=(
            "Use the Literature Search Tool to search for the research topic: "
            "{research_topic}\n\n"
            "Retrieve up to {max_results} peer-reviewed papers.\n\n"
            "After the search is complete, report:\n\n"
            "- Number of papers retrieved\n"
            "- Location of the CSV file\n"
            "- Location of the Markdown file\n"
            "- Location of the JSON file\n\n"
            "Do not invent references. Use only information returned by the tool."
        ),
        expected_output=(
            "A structured literature search report containing:\n"
            "1. Total number of papers retrieved\n"
            "2. Full file paths for the exported CSV, Markdown, and JSON files"
        ),
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
        memory=True,
    )

    result = crew.kickoff(
        inputs={"research_topic": research_topic, "max_results": max_results}
    )
    return str(result)
