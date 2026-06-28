from database import ResearchDatabase

from services.evidence_extractor import EvidenceExtractor

db = ResearchDatabase()

papers = db.get_all_paper_objects()

extractor = EvidenceExtractor()

paper = papers[0]

evidence = extractor.extract(paper)

print(evidence.model_dump())
