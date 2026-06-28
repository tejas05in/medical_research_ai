from database import ResearchDatabase
from services.evidence_extractor import EvidenceExtractor

db = ResearchDatabase()

extractor = EvidenceExtractor()

paper = db.get_all_paper_objects()[0]

print("Extracting evidence...")

evidence = extractor.extract(paper)

db.insert_evidence(evidence)

loaded = db.get_evidence(paper.pmid)

print()

print(loaded)
