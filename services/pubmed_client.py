from Bio import Entrez
from Bio import Medline
from utils.logger import logger
import os
from dotenv import load_dotenv

load_dotenv()

Entrez.email = os.getenv("NCBI_EMAIL", "your_email@example.com")


class PubMedClient:

    def search(self, query: str, max_results: int = 20):

        logger.info(f"Searching PubMed: {query}")

        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)

        record = Entrez.read(handle)

        logger.info(f"Retrieved {len(record['IdList'])} PMIDs")

        return record["IdList"]

    def fetch(self, pmids):

        ids = ",".join(pmids)

        handle = Entrez.efetch(db="pubmed", id=ids, rettype="medline", retmode="text")

        records = Medline.parse(handle)

        return list(records)
