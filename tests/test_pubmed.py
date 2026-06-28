from services.pubmed_client import PubMedClient
from services.pubmed_parser import parse_medline
from utils.exporters import PaperExporter

client = PubMedClient()

pmids = client.search("diabetic retinopathy artificial intelligence", max_results=10)

records = client.fetch(pmids)

papers = parse_medline(records)

exporter = PaperExporter()

csv_file = exporter.export_csv(papers)
md_file = exporter.export_markdown(papers)
json_file = exporter.export_json(papers)

print(f"CSV saved to: {csv_file}")
print(f"Markdown saved to: {md_file}")
print(f"JSON saved to: {json_file}")
