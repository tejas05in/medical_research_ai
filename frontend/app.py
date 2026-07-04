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
from utils.exporters import EvidenceExporter, PaperExporter  # noqa: E402

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
    for key in (
        "search_done",
        "papers",
        "crew_result",
        "enriched_query",
        "from_year",
        "extraction_done",
        "evidence_result",
    ):
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
            "Other sources use this range as a keyword hint in the query."
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

    # --- Evidence Extraction -------------------------------------------------
    st.markdown("---")
    st.subheader("Evidence Extraction")

    _db_sb = ResearchDatabase()
    _papers_in_db = len(_db_sb.get_all_papers())
    _evidence_count = len(_db_sb.get_all_evidence())
    _db_sb.close()

    if _papers_in_db > 0:
        st.caption(f"📊 {_evidence_count}/{_papers_in_db} papers extracted")

    _max_papers_raw = st.select_slider(
        "Max papers to extract",
        options=[5, 10, 20, 50, "All"],
        value="All",
        disabled=_papers_in_db == 0,
        help=(
            "Limit extraction for cost control during testing. "
            "'All' processes every paper without a cap."
        ),
    )

    if _evidence_count == 0:
        _extract_label = "🧬 Extract Evidence"
    elif _evidence_count < _papers_in_db:
        _extract_label = "🔄 Extract Remaining"
    else:
        _extract_label = "✅ Re-extract All"

    extract_clicked = st.button(
        _extract_label,
        type="primary",
        disabled=_papers_in_db == 0,
        width="stretch",
    )

    if _papers_in_db == 0:
        st.caption("Run a literature search first.")

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
                st.rerun()
            except Exception as exc:
                status.update(label="❌ Search failed", state="error", expanded=True)
                st.error(f"**Error:** {exc}")
                st.exception(exc)

# ---------------------------------------------------------------------------
# Evidence extraction trigger
# ---------------------------------------------------------------------------
if extract_clicked:
    _db_check = ResearchDatabase()
    _check_papers = _db_check.get_all_papers()
    _db_check.close()

    if not _check_papers:
        st.sidebar.error("No papers in the database. Run a literature search first.")
    else:
        max_papers_val = -1 if _max_papers_raw == "All" else int(_max_papers_raw)
        _limit_label = "all" if max_papers_val == -1 else str(max_papers_val)

        with st.status(
            f"� Extracting evidence ({_limit_label} papers)…",
            expanded=True,
        ) as status:
            st.write(
                f"Processing up to **{_limit_label}** paper(s) from "
                f"**{len(_check_papers)}** in the database…"
            )
            try:
                from tools.evidence_extraction_tool import (  # noqa: E402
                    EvidenceExtractionTool,
                )

                tool = EvidenceExtractionTool()
                evidence_result = tool._run(
                    max_papers=max_papers_val, delay_seconds=1.5
                )
                st.session_state["evidence_result"] = evidence_result
                st.session_state["extraction_done"] = True
                status.update(
                    label="✅ Evidence extraction complete!",
                    state="complete",
                    expanded=False,
                )
                st.rerun()
            except Exception as exc:
                status.update(
                    label="❌ Extraction failed", state="error", expanded=True
                )
                st.error(f"**Error:** {exc}")
                st.exception(exc)

# ---------------------------------------------------------------------------
# Results display — tabbed layout
# ---------------------------------------------------------------------------
_db_main = ResearchDatabase()
_all_papers_db = _db_main.get_all_papers()
_all_evidence_db = _db_main.get_all_evidence()
_db_main.close()

_show_search_tab = st.session_state.get("search_done")
_show_evidence_tab = bool(_all_evidence_db)

if _show_search_tab or _show_evidence_tab:
    tab1, tab2 = st.tabs(["📋 Search Results", "🧬 Evidence Table"])

    # -----------------------------------------------------------------------
    # Tab 1 — Search Results
    # -----------------------------------------------------------------------
    with tab1:
        if _show_search_tab:
            papers_to_show = _all_papers_db
            st.session_state["papers"] = papers_to_show

            # --- Metrics row ------------------------------------------------
            m1, m2, m3, m4 = st.columns(4)
            sources = {p.source for p in papers_to_show}
            pubmed_n = sum(1 for p in papers_to_show if p.source == "PubMed")
            m1.metric("Total Papers", len(papers_to_show))
            m2.metric("Databases Hit", len(sources))
            m3.metric("PubMed", pubmed_n)
            m4.metric("Other Sources", len(papers_to_show) - pubmed_n)

            # --- Results table ----------------------------------------------
            st.subheader("📋 Search Results")

            if papers_to_show:
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
                        for p in papers_to_show
                    ]
                )

                st.dataframe(
                    df,
                    width="stretch",
                    column_config={
                        "Source": st.column_config.TextColumn("Source", width="small"),
                        "Year": st.column_config.TextColumn("Year", width="small"),
                        "Title": st.column_config.TextColumn("Title", width="large"),
                        "Authors": st.column_config.TextColumn(
                            "Authors", width="medium"
                        ),
                        "Journal": st.column_config.TextColumn(
                            "Journal", width="medium"
                        ),
                        "PMID": st.column_config.TextColumn("PMID", width="small"),
                        "DOI": st.column_config.TextColumn("DOI", width="small"),
                    },
                    hide_index=True,
                )

                # --- Download buttons ----------------------------------------
                st.markdown("**Export results:**")
                exporter = PaperExporter()
                dl1, dl2, dl3 = st.columns(3)

                csv_path = exporter.export_csv(papers_to_show, filename="search_results.csv")
                with open(csv_path, "rb") as fh:
                    dl1.download_button(
                        "📥 CSV",
                        fh,
                        file_name="search_results.csv",
                        mime="text/csv",
                        width="stretch",
                    )

                md_path = exporter.export_markdown(
                    papers_to_show, filename="search_results.md"
                )
                with open(md_path, "rb") as fh:
                    dl2.download_button(
                        "📥 Markdown",
                        fh,
                        file_name="search_results.md",
                        mime="text/markdown",
                        width="stretch",
                    )

                json_path = exporter.export_json(
                    papers_to_show, filename="search_results.json"
                )
                with open(json_path, "rb") as fh:
                    dl3.download_button(
                        "📥 JSON",
                        fh,
                        file_name="search_results.json",
                        mime="application/json",
                        width="stretch",
                    )

                # --- Agent report --------------------------------------------
                with st.expander("🤖 Agent Report", expanded=False):
                    st.text(st.session_state.get("crew_result", ""))

                # --- Abstract viewer ----------------------------------------
                st.divider()
                st.subheader("📄 Abstracts")

                for paper in papers_to_show:
                    _label = (
                        f"{paper.year}  ·  {paper.source}  ·  "
                        f"{paper.title[:85]}{'…' if len(paper.title) > 85 else ''}"
                    )
                    with st.expander(_label):
                        c1, c2 = st.columns(2)
                        c1.markdown(
                            f"**Authors:** {format_authors(paper.authors) or 'N/A'}"
                        )
                        c1.markdown(f"**Journal:** {paper.journal or 'N/A'}")
                        c2.markdown(f"**PMID:** {paper.pmid or 'N/A'}")
                        c2.markdown(f"**DOI:** {paper.doi or 'N/A'}")
                        if paper.url:
                            c2.markdown(f"[🔗 View Paper]({paper.url})")
                        st.markdown("---")
                        st.write(paper.abstract or "*No abstract available.*")
            else:
                st.info("No papers found. Run a literature search first.")
        else:
            st.info("Run a literature search to see results here.")

    # -----------------------------------------------------------------------
    # Tab 2 — Evidence Table
    # -----------------------------------------------------------------------
    with tab2:
        if _show_evidence_tab:
            paper_lookup = {p.id: p for p in _all_papers_db}
            total_evidence = len(_all_evidence_db)
            total_papers = len(_all_papers_db)
            coverage_pct = (
                round(100 * total_evidence / total_papers) if total_papers > 0 else 0
            )
            papers_without = total_papers - total_evidence
            llm_provider_label = (
                (_all_evidence_db[0].llm_provider or "N/A")
                if _all_evidence_db
                else "N/A"
            )

            # --- Metrics row ------------------------------------------------
            e1, e2, e3, e4 = st.columns(4)
            e1.metric("Evidence Records", total_evidence)
            e2.metric("Coverage", f"{coverage_pct}%")
            e3.metric("Papers Without Evidence", papers_without)
            e4.metric("LLM Provider", llm_provider_label)

            # --- Evidence summary table -------------------------------------
            st.subheader("🧬 Evidence Summary Table")

            ev_rows = []
            for ev in _all_evidence_db:
                _paper = paper_lookup.get(ev.paper_id)
                _title = _paper.title if _paper else f"Paper ID {ev.paper_id}"
                _key_finding = ev.key_findings[0] if ev.key_findings else ""
                ev_rows.append(
                    {
                        "Title": ((_title[:80] + "…") if len(_title) > 80 else _title),
                        "Year": _paper.year if _paper else "",
                        "Study Design": ev.study_design or "",
                        "Population": ev.population or "",
                        "Sample Size": (str(ev.sample_size) if ev.sample_size else ""),
                        "Country": ev.country or "",
                        "Intervention": ev.intervention or "",
                        "Key Finding": _key_finding,
                        "Conclusion": ev.conclusion or "",
                        "Risk of Bias": ev.risk_of_bias or "",
                    }
                )

            ev_df = pd.DataFrame(ev_rows)
            st.dataframe(
                ev_df,
                width="stretch",
                column_config={
                    "Title": st.column_config.TextColumn("Title", width="large"),
                    "Year": st.column_config.TextColumn("Year", width="small"),
                    "Study Design": st.column_config.TextColumn(
                        "Study Design", width="medium"
                    ),
                    "Population": st.column_config.TextColumn(
                        "Population", width="medium"
                    ),
                    "Sample Size": st.column_config.TextColumn(
                        "Sample Size", width="small"
                    ),
                    "Country": st.column_config.TextColumn("Country", width="small"),
                    "Intervention": st.column_config.TextColumn(
                        "Intervention", width="medium"
                    ),
                    "Key Finding": st.column_config.TextColumn(
                        "Key Finding", width="large"
                    ),
                    "Conclusion": st.column_config.TextColumn(
                        "Conclusion", width="large"
                    ),
                    "Risk of Bias": st.column_config.TextColumn(
                        "Risk of Bias", width="small"
                    ),
                },
                hide_index=True,
            )

            # --- Export buttons ---------------------------------------------
            st.markdown("**Export evidence:**")
            ev_exporter = EvidenceExporter()
            edl1, edl2, edl3 = st.columns(3)

            ev_csv_path = ev_exporter.export_csv(
                _all_evidence_db, filename="evidence.csv"
            )
            with open(ev_csv_path, "rb") as fh:
                edl1.download_button(
                    "📥 CSV",
                    fh,
                    file_name="evidence.csv",
                    mime="text/csv",
                    width="stretch",
                )

            ev_md_path = ev_exporter.export_markdown(
                _all_evidence_db, filename="evidence.md"
            )
            with open(ev_md_path, "rb") as fh:
                edl2.download_button(
                    "📥 Markdown",
                    fh,
                    file_name="evidence.md",
                    mime="text/markdown",
                    width="stretch",
                )

            ev_json_path = ev_exporter.export_json(
                _all_evidence_db, filename="evidence.json"
            )
            with open(ev_json_path, "rb") as fh:
                edl3.download_button(
                    "📥 JSON",
                    fh,
                    file_name="evidence.json",
                    mime="application/json",
                    width="stretch",
                )

            # --- Agent report expander --------------------------------------
            if st.session_state.get("evidence_result"):
                with st.expander("🤖 Agent Report", expanded=False):
                    st.text(st.session_state.get("evidence_result", ""))

            # --- Detailed evidence expanders --------------------------------
            st.divider()
            st.subheader("📄 Detailed Evidence Records")

            for ev in _all_evidence_db:
                _paper = paper_lookup.get(ev.paper_id)
                _title = _paper.title if _paper else f"Paper ID {ev.paper_id}"
                _year = _paper.year if _paper else ""
                _exp_label = (
                    f"{_year}  ·  {_title[:75]}{'…' if len(_title) > 75 else ''}"
                )

                with st.expander(_exp_label):
                    c1, c2 = st.columns(2)

                    with c1:
                        st.markdown("**Study Design:**")
                        st.write(ev.study_design or "*Not reported*")
                        st.markdown("**Population:**")
                        st.write(ev.population or "*Not reported*")
                        st.markdown("**Sample Size:**")
                        st.write(
                            str(ev.sample_size) if ev.sample_size else "*Not reported*"
                        )
                        st.markdown("**Country:**")
                        st.write(ev.country or "*Not reported*")
                        st.markdown("**Intervention:**")
                        st.write(ev.intervention or "*Not reported*")
                        st.markdown("**Comparator:**")
                        st.write(ev.comparator or "*Not reported*")

                    with c2:
                        if ev.primary_outcomes:
                            st.markdown("**Primary Outcomes:**")
                            for _o in ev.primary_outcomes:
                                st.markdown(f"• {_o}")
                        if ev.secondary_outcomes:
                            st.markdown("**Secondary Outcomes:**")
                            for _o in ev.secondary_outcomes:
                                st.markdown(f"• {_o}")
                        if ev.key_findings:
                            st.markdown("**Key Findings:**")
                            for _f in ev.key_findings:
                                st.markdown(f"• {_f}")
                        if ev.limitations:
                            st.markdown("**Limitations:**")
                            for _l in ev.limitations:
                                st.markdown(f"• {_l}")

                    st.markdown("---")
                    st.markdown(f"**Conclusion:** {ev.conclusion or '*Not reported*'}")
                    st.markdown(
                        f"**Risk of Bias:** {ev.risk_of_bias or '*Not assessed*'}"
                    )
                    st.caption(
                        f"LLM: {ev.llm_provider} / {ev.llm_model}  ·  "
                        f"Version: {ev.extraction_prompt_version}  ·  "
                        f"Extracted: {ev.extracted_at}"
                    )
        else:
            st.info(
                "No evidence extracted yet. "
                "Use **🧬 Extract Evidence** in the sidebar after running a search."
            )
