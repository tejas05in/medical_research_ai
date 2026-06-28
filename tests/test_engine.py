from services.literature_engine import LiteratureSearchEngine

from database import ResearchDatabase

engine = LiteratureSearchEngine()

db = ResearchDatabase()

papers = engine.search("machine learning diabetic retinopathy", max_results=5)

db.log_search(
    query="machine learning diabetic retinopathy",
    source="PubMed",
    number_of_results=len(papers),
)

db.insert_many(papers)

print("Database Updated")

rows = db.get_all_papers()

print(f"{len(rows)} papers in database.")
