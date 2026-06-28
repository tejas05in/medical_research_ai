"""
Test: CrewAI Evidence Extraction
=================================
Test A — Unit: calls EvidenceExtractionTool directly (no crew overhead),
         processes at most 10 papers (rate-limit safe).

Test B — Integration: runs the full evidence_crew via crewai Crew API,
         passes max_papers=10 and delay_seconds=1.5 as crew inputs.

Run from the project root:
    python tests/test_crewai_evidence_extraction.py

Environment variables required (at least one LLM provider must be set):
    LLM_PROVIDER        gemini | openai  (default: gemini)
    GEMINI_API_KEY      required when LLM_PROVIDER=gemini
    OPENAI_API_KEY      required when LLM_PROVIDER=openai
    OPENAI_API_KEY      also required for the agent's gpt-4.1-mini LLM (Test B)
"""

import sys
import os

# Allow imports from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

MAX_PAPERS = 10  # Keep low for rate-limit-safe testing
DELAY_SECS = 1.5  # Seconds between LLM calls


# ---------------------------------------------------------------------------
# Test A — Unit: tool called directly
# ---------------------------------------------------------------------------


def test_a_tool_direct():
    """Call EvidenceExtractionTool._run() directly and verify the summary."""
    print("\n[Test A] Direct tool call (max_papers=10) ...")

    from tools.evidence_extraction_tool import EvidenceExtractionTool
    from database import ResearchDatabase

    db = ResearchDatabase()
    total_papers = len(db.get_all_papers())
    db.close()

    if total_papers == 0:
        print(f"  SKIP — no papers in database. Run the search crew first.")
        return True

    tool = EvidenceExtractionTool()
    result = tool._run(max_papers=MAX_PAPERS, delay_seconds=DELAY_SECS)

    print(result)

    assert "Evidence extraction complete." in result, "Missing completion header"
    assert "CSV" in result, "Missing CSV path"
    assert "Markdown" in result, "Missing Markdown path"
    assert "JSON" in result, "Missing JSON path"

    # Verify DB has evidence rows
    db = ResearchDatabase()
    evidence_rows = db.get_all_evidence()
    db.close()

    assert len(evidence_rows) > 0, "No evidence rows found in database"
    print(f"  DB evidence rows: {len(evidence_rows)}")

    # Verify exported files exist
    from pathlib import Path

    for label, keyword in [("CSV", "csv"), ("Markdown", "md"), ("JSON", "json")]:
        assert Path(f"outputs/{keyword}/evidence.{keyword}").exists() or any(
            keyword in line for line in result.splitlines()
        ), f"{label} output file not found"

    print(
        f"  [{PASS}] Tool returned valid summary with {len(evidence_rows)} evidence rows"
    )
    return True


# ---------------------------------------------------------------------------
# Test B — Integration: full crew run
# ---------------------------------------------------------------------------


def test_b_crew_run():
    """
    Run the evidence_crew via the CrewAI Python API with max_papers=10.

    This test requires:
    - OPENAI_API_KEY for the agent's gpt-4.1-mini orchestration LLM
    - The LLM_PROVIDER extraction LLM key (GEMINI_API_KEY or OPENAI_API_KEY)
    """
    print("\n[Test B] Full crew run (max_papers=10) ...")

    from database import ResearchDatabase

    db = ResearchDatabase()
    total_papers = len(db.get_all_papers())
    db.close()

    if total_papers == 0:
        print("  SKIP — no papers in database. Run the search crew first.")
        return True

    if not os.getenv("OPENAI_API_KEY"):
        print("  SKIP — OPENAI_API_KEY not set (needed for agent's gpt-4.1-mini).")
        return True

    from crewai import Crew, Agent, Task
    from crewai.project import CrewBase

    # Load agent and task from their JSONC specs via CrewAI's config loader
    from tools.evidence_extraction_tool import EvidenceExtractionTool

    tool = EvidenceExtractionTool()

    agent = Agent(
        role="Medical Evidence Extraction Specialist",
        goal=(
            "Extract structured clinical evidence from all retrieved biomedical "
            "articles stored in the research database."
        ),
        backstory=(
            "You are a seasoned systematic reviewer and clinical epidemiologist. "
            "You apply rigorous, standardised extraction methods to transform raw "
            "biomedical abstracts into structured evidence tables."
        ),
        llm="openai/gpt-4.1-mini",
        tools=[tool],
        verbose=False,
        allow_delegation=False,
    )

    task = Task(
        description=(
            f"Use the Evidence Extraction Tool to extract structured clinical "
            f"evidence from biomedical papers stored in the research database. "
            f"Call the tool with max_papers={MAX_PAPERS} and "
            f"delay_seconds={DELAY_SECS}. "
            f"The tool skips papers that already have evidence stored. "
            f"Report processed, skipped, failed counts and output file paths."
        ),
        expected_output=("A plain-text extraction summary with counts and file paths."),
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        verbose=True,
        memory=False,
    )

    result = crew.kickoff(
        inputs={"max_papers": MAX_PAPERS, "delay_seconds": DELAY_SECS}
    )

    output = str(result)
    print(output)

    assert output, "Crew returned empty result"
    print(f"  [{PASS}] Crew completed successfully")
    return True


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_all():
    results = {}

    try:
        results["A — Tool direct"] = test_a_tool_direct()
    except Exception as e:
        print(f"  [{FAIL}] Test A raised: {e}")
        results["A — Tool direct"] = False

    try:
        results["B — Crew run"] = test_b_crew_run()
    except Exception as e:
        print(f"  [{FAIL}] Test B raised: {e}")
        results["B — Crew run"] = False

    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    for name, passed in results.items():
        status = PASS if passed else FAIL
        print(f"  {status}  {name}")

    if all(results.values()):
        print("\nAll tests passed.")
        sys.exit(0)
    else:
        print("\nSome tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    run_all()
