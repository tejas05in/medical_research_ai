from database import ResearchDatabase

from services.evidence_extractor import EvidenceExtractor

db = ResearchDatabase()

papers = db.get_all_papers()

extractor = EvidenceExtractor()

paper = papers[0]

evidence = extractor.extract(paper, paper.id)

print(evidence.model_dump())
