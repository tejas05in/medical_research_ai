"""
Medical Research AI — Streamlit Literature Search Frontend

Launch from the project root:
    streamlit run frontend/app.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Path & environment setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
# Set CWD to project root so all relative file paths (DB, exports) resolve
# correctly regardless of where 'streamlit run' was invoked from.
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "frontend"))

load_dotenv(PROJECT_ROOT / ".env")

from database.database import ResearchDatabase  # noqa: E402
from utils.exporters import PaperExporter  # noqa: E402

# ---------------------------------------------------------------------------
# Reset helpers
# ---------------------------------------------------------------------------


def _delete_output_files() -> int:
    """Delete all export files under outputs/csv, outputs/json, outputs/markdown.
    Returns the number of files deleted."""
    deleted = 0
    for subdir in ("csv", "json", "markdown"):
        folder = PROJECT_ROOT / "outputs" / subdir
        if folder.exists():
            for f in folder.iterdir():
                if f.is_file():
                    f.unlink()
                    deleted += 1
    return deleted


def _reset_session_state() -> None:
    """Clear all search-related keys from Streamlit session state."""
    for key in ("search_done", "papers", "crew_result", "enriched_query", "from_year"):
        st.session_state.pop(key, None)


# ---------------------------------------------------------------------------
# Page configuration  (must be the first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Medical Research AI",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🔬 Medical Research AI")
st.caption(
    "Systematic literature search across "
    "**PubMed · EuropePMC · OpenAlex · CrossRef**"
)

# ---------------------------------------------------------------------------
# Sidebar — Search form
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Search Parameters")
    st.markdown("---")

    query = st.text_area(
        "Research Topic *",
        placeholder="e.g. type 2 diabetes management in elderly patients",
        height=120,
        help=(
            "Enter the medical topic or research question you want to search for. "
            "Plain English or Boolean queries are both supported."
        ),
    )

    years_back = st.slider(
        "Papers from the last N years",
        min_value=1,
        max_value=10,
        value=5,
        step=1,
        help=(
            "Restricts PubMed results via the [PDAT] field. "
            "Other sources are filtered post-retrieval by the paper's year field."
        ),
    )

    max_results = st.slider(
        "Max papers per database",
        min_value=5,
        max_value=50,
        value=20,
        step=5,
        help="Maximum number of papers fetched from each of the 4 databases.",
    )

    location = st.text_input(
        "Place of Study (optional)",
        placeholder="e.g. India, Harvard, Mayo Clinic",
        help=(
            "Filters by institution or country affiliation. "
            "Applied as [Affiliation] for PubMed; treated as a keyword for other sources."
        ),
    )

    st.markdown("---")
    search_clicked = st.button("🔍 Search Literature", type="primary", width="stretch")

    st.markdown("---")
    if st.button("🗑️ Reset All Data", type="secondary", width="stretch"):
        db = ResearchDatabase()
        db.clear_all()
        db.close()
        files_deleted = _delete_output_files()
        _reset_session_state()
        st.toast(f"Reset complete — {files_deleted} export file(s) deleted.", icon="✅")
        st.rerun()

    st.markdown("---")
    st.caption(
        "**Date filter:** `[PDAT]` for PubMed; "
        "year post-filter for EuropePMC / OpenAlex / CrossRef.\n\n"
        "**Location filter:** `[Affiliation]` for PubMed."
    )

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def build_enriched_query(base_query: str, years_back: int, location: str) -> str:
    """Append PubMed-compatible date and affiliation filters to the query."""
    current_year = datetime.now().year
    from_year = current_year - years_back
    enriched = base_query.strip()
    if location.strip():
        enriched += f' AND "{location.strip()}"[Affiliation]'
    enriched += f" AND ({from_year}:{current_year}[PDAT])"
    return enriched


def safe_year(year_str: str) -> int | None:
    """Parse the first 4 characters of a year string to int; return None on failure."""
    try:
        return int(str(year_str).strip()[:4])
    except (ValueError, TypeError):
        return None


def format_authors(authors: list) -> str:
    if not authors:
        return ""
    if len(authors) <= 2:
        return ", ".join(authors)
    return f"{authors[0]} et al."


# ---------------------------------------------------------------------------
# Search trigger
# ---------------------------------------------------------------------------
if search_clicked:
    if not query.strip():
        st.sidebar.error("Please enter a research topic.")
    else:
        enriched = build_enriched_query(query, years_back, location)
        from_year_val = datetime.now().year - years_back

        st.session_state["enriched_query"] = enriched
        st.session_state["from_year"] = from_year_val
        st.session_state["search_done"] = False
        st.session_state["papers"] = []

        with st.status("🤖 Running literature search agent…", expanded=True) as status:
            st.write(f"**Enriched query:** `{enriched}`")
            st.write(
                f"Searching PubMed, EuropePMC, OpenAlex, and CrossRef "
                f"(up to **{max_results}** papers each)…"
            )
            try:
                from crew_runner import run_literature_search_crew  # noqa: E402

                crew_result = run_literature_search_crew(enriched, max_results)
                st.session_state["crew_result"] = crew_result
                st.session_state["search_done"] = True
                status.update(
                    label="✅ Search complete!", state="complete", expanded=False
                )
            except Exception as exc:
                status.update(label="❌ Search failed", state="error", expanded=True)
                st.error(f"**Error:** {exc}")
                st.exception(exc)

# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------
if st.session_state.get("search_done"):
    db = ResearchDatabase()
    all_papers = db.get_all_papers()
    db.close()

    from_year_val = st.session_state.get("from_year", 0)

    # Post-filter by year (covers non-PubMed sources that ignore [PDAT])
    filtered = []
    for p in all_papers:
        yr = safe_year(p.year)
        if yr is None or yr >= from_year_val:
            filtered.append(p)

    st.session_state["papers"] = filtered

    st.divider()

    # --- Metrics row --------------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    sources = {p.source for p in filtered}
    pubmed_n = sum(1 for p in filtered if p.source == "PubMed")
    m1.metric("Total Papers", len(filtered))
    m2.metric("Databases Hit", len(sources))
    m3.metric("PubMed", pubmed_n)
    m4.metric("Other Sources", len(filtered) - pubmed_n)

    # --- Results table ------------------------------------------------------
    st.subheader("📋 Search Results")

    if filtered:
        df = pd.DataFrame(
            [
                {
                    "Source": p.source,
                    "Year": p.year,
                    "Title": p.title,
                    "Authors": format_authors(p.authors),
                    "Journal": p.journal,
                    "PMID": p.pmid or "",
                    "DOI": p.doi or "",
                }
                for p in filtered
            ]
        )

        st.dataframe(
            df,
            width="stretch",
            column_config={
                "Source": st.column_config.TextColumn("Source", width="small"),
                "Year": st.column_config.TextColumn("Year", width="small"),
                "Title": st.column_config.TextColumn("Title", width="large"),
                "Authors": st.column_config.TextColumn("Authors", width="medium"),
                "Journal": st.column_config.TextColumn("Journal", width="medium"),
                "PMID": st.column_config.TextColumn("PMID", width="small"),
                "DOI": st.column_config.TextColumn("DOI", width="small"),
            },
            hide_index=True,
        )

        # --- Download buttons -----------------------------------------------
        st.markdown("**Export results:**")
        exporter = PaperExporter()
        dl1, dl2, dl3 = st.columns(3)

        csv_path = exporter.export_csv(filtered, filename="search_results.csv")
        with open(csv_path, "rb") as fh:
            dl1.download_button(
                "📥 CSV",
                fh,
                file_name="search_results.csv",
                mime="text/csv",
                width="stretch",
            )

        md_path = exporter.export_markdown(filtered, filename="search_results.md")
        with open(md_path, "rb") as fh:
            dl2.download_button(
                "📥 Markdown",
                fh,
                file_name="search_results.md",
                mime="text/markdown",
                width="stretch",
            )

        json_path = exporter.export_json(filtered, filename="search_results.json")
        with open(json_path, "rb") as fh:
            dl3.download_button(
                "📥 JSON",
                fh,
                file_name="search_results.json",
                mime="application/json",
                width="stretch",
            )

        # --- Agent report ---------------------------------------------------
        with st.expander("🤖 Agent Report", expanded=False):
            st.text(st.session_state.get("crew_result", ""))

        # --- Abstract viewer ------------------------------------------------
        st.divider()
        st.subheader("📄 Abstracts")

        for paper in filtered:
            label = (
                f"{paper.year}  ·  {paper.source}  ·  "
                f"{paper.title[:85]}{'…' if len(paper.title) > 85 else ''}"
            )
            with st.expander(label):
                c1, c2 = st.columns(2)
                c1.markdown(f"**Authors:** {format_authors(paper.authors) or 'N/A'}")
                c1.markdown(f"**Journal:** {paper.journal or 'N/A'}")
                c2.markdown(f"**PMID:** {paper.pmid or 'N/A'}")
                c2.markdown(f"**DOI:** {paper.doi or 'N/A'}")
                if paper.url:
                    c2.markdown(f"[🔗 View Paper]({paper.url})")
                st.markdown("---")
                st.write(paper.abstract or "*No abstract available.*")

    else:
        st.info("No papers found matching your search criteria.")
