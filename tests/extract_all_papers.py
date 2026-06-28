from database import ResearchDatabase
from services.evidence_extractor import EvidenceExtractor

db = ResearchDatabase()

extractor = EvidenceExtractor()

papers = db.get_all_papers()

for paper in papers:

    evidence = extractor.extract(
        paper,
        paper.id,
    )

    db.insert_evidence(evidence)
