from database import ResearchDatabase
from services.evidence_extractor import EvidenceExtractor

db = ResearchDatabase()

extractor = EvidenceExtractor()

paper = db.get_all_papers()[0]

print("Extracting evidence...")

evidence = extractor.extract(paper, paper.id)

db.insert_evidence(evidence)

loaded = db.get_evidence(paper.id)

print()

print(loaded)
