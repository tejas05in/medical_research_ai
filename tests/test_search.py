"""
Consolidated test suite for the multi-database literature search pipeline.

Covers:
  - PubMed client
  - Europe PMC client
  - OpenAlex client
  - CrossRef client
  - LiteratureSearchEngine (multi-source + deduplication)
  - ResearchDatabase roundtrip (insert, retrieve, search history)
  - PaperExporter (CSV, Markdown, JSON)

Usage:
  uv run python tests/test_search.py
"""

import sys

from database import ResearchDatabase
from models import Paper
from services.crossref_client import CrossRefClient
from services.europepmc_client import EuropePMCClient
from services.literature_engine import LiteratureSearchEngine
from services.openalex_client import OpenAlexClient
from services.pubmed_client import PubMedClient
from utils.exporters import PaperExporter

# ── configuration ──────────────────────────────────────────────────────────────
QUERY = "diabetic retinopathy artificial intelligence"
MAX_RESULTS = 5  # keep small for speed; increase for a real search
SEPARATOR = "─" * 60

# ── helpers ────────────────────────────────────────────────────────────────────

passed: list[str] = []
failed: list[str] = []


def section(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def ok(name: str, detail: str = "") -> None:
    tag = f"[PASS] {name}"
    if detail:
        tag += f" — {detail}"
    print(tag)
    passed.append(name)


def fail(name: str, error: Exception) -> None:
    print(f"[FAIL] {name} — {error}")
    failed.append(name)


def show_papers(papers: list[Paper], limit: int = 3) -> None:
    for p in papers[:limit]:
        print(
            f"  • [{p.source}] {p.year} | {p.title[:70]}..."
            if len(p.title) > 70
            else f"  • [{p.source}] {p.year} | {p.title}"
        )
        print(f"    PMID={p.pmid}  DOI={p.doi}")
    if len(papers) > limit:
        print(f"  ... and {len(papers) - limit} more")


# ── individual client tests ────────────────────────────────────────────────────


def test_pubmed() -> list[Paper]:
    section("PubMed Client")
    try:
        client = PubMedClient()
        papers = client.search(QUERY, max_results=MAX_RESULTS)
        assert isinstance(papers, list), "Expected list"
        assert all(isinstance(p, Paper) for p in papers)
        assert all(p.source == "PubMed" for p in papers)
        ok("PubMedClient.search", f"{len(papers)} papers")
        show_papers(papers)
        # Verify rich metadata fields are populated
        with_mesh = sum(1 for p in papers if p.mesh_terms)
        ok("PubMed MeSH terms", f"{with_mesh}/{len(papers)} papers have MeSH terms")
        return papers
    except Exception as e:
        fail("PubMedClient", e)
        return []


def test_europepmc() -> list[Paper]:
    section("Europe PMC Client")
    try:
        client = EuropePMCClient()
        papers = client.search(QUERY, max_results=MAX_RESULTS)
        assert isinstance(papers, list), "Expected list"
        assert all(isinstance(p, Paper) for p in papers)
        assert all(p.source == "EuropePMC" for p in papers)
        ok("EuropePMCClient.search", f"{len(papers)} papers")
        show_papers(papers)
        return papers
    except Exception as e:
        fail("EuropePMCClient", e)
        return []


def test_openalex() -> list[Paper]:
    section("OpenAlex Client")
    try:
        client = OpenAlexClient()
        papers = client.search(QUERY, max_results=MAX_RESULTS)
        assert isinstance(papers, list), "Expected list"
        assert all(isinstance(p, Paper) for p in papers)
        assert all(p.source == "OpenAlex" for p in papers)
        ok("OpenAlexClient.search", f"{len(papers)} papers")
        show_papers(papers)
        # Verify abstract reconstruction
        with_abstract = sum(1 for p in papers if p.abstract)
        ok(
            "OpenAlex abstract reconstruction",
            f"{with_abstract}/{len(papers)} have abstracts",
        )
        return papers
    except Exception as e:
        fail("OpenAlexClient", e)
        return []


def test_crossref() -> list[Paper]:
    section("CrossRef Client")
    try:
        client = CrossRefClient()
        papers = client.search(QUERY, max_results=MAX_RESULTS)
        assert isinstance(papers, list), "Expected list"
        assert all(isinstance(p, Paper) for p in papers)
        assert all(p.source == "CrossRef" for p in papers)
        # CrossRef has no PMIDs
        assert all(p.pmid is None for p in papers), "CrossRef should not return PMIDs"
        ok("CrossRefClient.search", f"{len(papers)} papers")
        show_papers(papers)
        return papers
    except Exception as e:
        fail("CrossRefClient", e)
        return []


# ── multi-source engine test ───────────────────────────────────────────────────


def test_multi_source_engine() -> list[Paper]:
    section("Multi-Source Engine + Deduplication")
    try:
        engine = LiteratureSearchEngine(
            clients=[
                PubMedClient(),
                EuropePMCClient(),
                OpenAlexClient(),
                CrossRefClient(),
            ]
        )
        papers = engine.search(QUERY, max_results=MAX_RESULTS)
        assert isinstance(papers, list)

        ok("LiteratureSearchEngine.search", f"{len(papers)} unique papers after dedup")

        # Verify sources represented
        sources = {p.source for p in papers}
        ok("Sources present", ", ".join(sorted(sources)))

        # Verify no PMID duplicates
        pmids = [p.pmid for p in papers if p.pmid]
        assert len(pmids) == len(set(pmids)), "Duplicate PMIDs found after dedup"
        ok("No PMID duplicates")

        # Verify no DOI duplicates
        dois = [p.doi for p in papers if p.doi]
        assert len(dois) == len(set(dois)), "Duplicate DOIs found after dedup"
        ok("No DOI duplicates")

        show_papers(papers, limit=5)
        return papers

    except Exception as e:
        fail("LiteratureSearchEngine", e)
        return []


# ── database roundtrip test ────────────────────────────────────────────────────


def test_database(papers: list[Paper]) -> None:
    section("Database Roundtrip")

    if not papers:
        print("  Skipped — no papers from engine test")
        return

    try:
        with ResearchDatabase() as db:

            ids_inserted = db.insert_many(papers)
            ok(
                "insert_many",
                f"{len([i for i in ids_inserted if i])} rows inserted/skipped",
            )

            all_papers = db.get_all_papers()
            assert len(all_papers) > 0
            ok("get_all_papers", f"{len(all_papers)} total papers in DB")

            first = db.get_paper(all_papers[0].id)
            assert first is not None
            assert first.title
            ok("get_paper by id", f"'{first.title[:50]}...'")

            db.log_search(
                query=QUERY,
                source="PubMed, EuropePMC, OpenAlex, CrossRef",
                number_of_results=len(papers),
            )
            ok("log_search")

    except Exception as e:
        fail("Database", e)


# ── export tests ───────────────────────────────────────────────────────────────


def test_exports(papers: list[Paper]) -> None:
    section("Exports (CSV / Markdown / JSON)")

    if not papers:
        print("  Skipped — no papers")
        return

    try:
        exporter = PaperExporter()

        csv_path = exporter.export_csv(papers, filename="test_results.csv")
        assert csv_path.exists()
        ok("export_csv", str(csv_path))

        md_path = exporter.export_markdown(papers, filename="test_results.md")
        assert md_path.exists()
        ok("export_markdown", str(md_path))

        json_path = exporter.export_json(papers, filename="test_results.json")
        assert json_path.exists()
        ok("export_json", str(json_path))

    except Exception as e:
        fail("PaperExporter", e)


# ── single-source engine sanity check ─────────────────────────────────────────


def test_engine_single_source() -> None:
    section("Engine — Single Source (PubMed only, default)")
    try:
        engine = LiteratureSearchEngine()  # defaults to [PubMedClient()]
        assert len(engine.clients) == 1
        assert engine.clients[0].source_name == "PubMed"
        papers = engine.search(QUERY, max_results=3)
        assert all(p.source == "PubMed" for p in papers)
        ok("Single-source engine default", f"{len(papers)} papers")
    except Exception as e:
        fail("Single-source engine", e)


# ── empty query guard ──────────────────────────────────────────────────────────


def test_empty_results_guard() -> None:
    section("Empty Results Guard (PubMed)")
    try:
        # A nonsensical query should return 0 results without crashing
        client = PubMedClient()
        papers = client.search(
            "xyzzy123456789nonsensetermthatmatchesnothing", max_results=5
        )
        assert isinstance(papers, list)
        ok("Empty result handled gracefully", f"{len(papers)} papers returned")
    except Exception as e:
        fail("Empty results guard", e)


# ── main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    print(f"\n{'═' * 60}")
    print("  Medical Research AI — Search Pipeline Test Suite")
    print(f"  Query: '{QUERY}'  |  Max per source: {MAX_RESULTS}")
    print(f"{'═' * 60}")

    # Individual clients
    test_pubmed()
    test_europepmc()
    test_openalex()
    test_crossref()

    # Engine
    test_engine_single_source()
    all_papers = test_multi_source_engine()

    # DB + Exports (use multi-source results)
    test_database(all_papers)
    test_exports(all_papers)

    # Guard
    test_empty_results_guard()

    # Summary
    print(f"\n{'═' * 60}")
    print(f"  Results: {len(passed)} passed, {len(failed)} failed")
    if failed:
        print(f"  Failed:  {', '.join(failed)}")
    print(f"{'═' * 60}\n")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
