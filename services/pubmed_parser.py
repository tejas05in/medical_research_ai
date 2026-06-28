from models import Paper


def parse_medline(records):

    papers = []

    for record in records:

        doi = None

        if "AID" in record:

            for aid in record["AID"]:

                if "[doi]" in aid.lower():
                    doi = aid.split(" ")[0]
                    break

        pmid = record.get("PMID", "")

        paper = Paper(
            pmid=pmid,
            doi=doi,
            title=record.get("TI", ""),
            authors=record.get("AU", []),
            journal=record.get("JT", ""),
            year=record.get("DP", "")[:4],
            abstract=record.get("AB", ""),
            keywords=record.get("OT", []),
            mesh_terms=record.get("MH", []),
            publication_types=record.get("PT", []),
            language=record.get("LA", ["eng"])[0] if record.get("LA") else "eng",
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
        )

        papers.append(paper)

    return papers
