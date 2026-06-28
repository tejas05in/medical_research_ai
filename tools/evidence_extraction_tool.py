import time
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from database import ResearchDatabase
from services.evidence_extractor import EvidenceExtractor
from utils.exporters import EvidenceExporter
from utils.logger import logger


class EvidenceExtractionInput(BaseModel):
    max_papers: int = Field(
        default=10,
        description=(
            "Maximum number of papers to process. "
            "Use 10 for rate-limit-safe testing. "
            "Use -1 to process all papers without a limit."
        ),
    )
    delay_seconds: float = Field(
        default=1.5,
        description="Seconds to pause between LLM calls to respect rate limits.",
    )


class EvidenceExtractionTool(BaseTool):
    name: str = "Evidence Extraction Tool"

    description: str = (
        "Reads retrieved biomedical papers from the research database, "
        "extracts structured clinical evidence (study design, population, "
        "outcomes, findings) using an LLM, stores the results back in the "
        "database, and exports them as CSV, Markdown, and JSON. "
        "Skips papers that already have evidence extracted. "
        "Set max_papers=10 for testing; max_papers=-1 for full extraction."
    )

    args_schema: Type[BaseModel] = EvidenceExtractionInput

    def _run(self, max_papers: int = 10, delay_seconds: float = 1.5) -> str:

        db = ResearchDatabase()
        extractor = EvidenceExtractor()
        exporter = EvidenceExporter()

        extracted_count = 0
        skipped_count = 0
        failed_count = 0
        failed_ids = []

        try:

            all_papers = db.get_all_papers()

            pending = [p for p in all_papers if not db.evidence_exists(p.id)]

            if max_papers > 0:
                pending = pending[:max_papers]

            logger.info(
                f"Evidence extraction starting: "
                f"{len(pending)} pending | "
                f"{len(all_papers) - len(pending)} already extracted"
            )

            skipped_count = len(all_papers) - len(pending)

            for i, paper in enumerate(pending, start=1):

                try:

                    logger.info(
                        f"[{i}/{len(pending)}] Extracting evidence for "
                        f"paper_id={paper.id} — {paper.title[:60]}..."
                    )

                    evidence = extractor.extract(paper, paper.id)

                    db.insert_evidence(evidence)

                    extracted_count += 1

                    logger.info(
                        f"[{i}/{len(pending)}] Stored evidence for paper_id={paper.id}"
                    )

                except Exception as exc:

                    failed_count += 1
                    failed_ids.append(paper.id)
                    logger.error(
                        f"[{i}/{len(pending)}] Failed paper_id={paper.id}: {exc}"
                    )

                if i < len(pending):
                    time.sleep(delay_seconds)

            all_evidence = db.get_all_evidence()
            csv_file = exporter.export_csv(all_evidence)
            md_file = exporter.export_markdown(all_evidence)
            json_file = exporter.export_json(all_evidence)

        finally:
            db.close()

        failed_note = f"\n\nFailed paper IDs: {failed_ids}" if failed_ids else ""

        return (
            f"Evidence extraction complete.\n\n"
            f"Papers processed : {extracted_count}\n"
            f"Already extracted: {skipped_count}\n"
            f"Failed           : {failed_count}"
            f"{failed_note}\n\n"
            f"CSV      : {csv_file}\n"
            f"Markdown : {md_file}\n"
            f"JSON     : {json_file}"
        )
