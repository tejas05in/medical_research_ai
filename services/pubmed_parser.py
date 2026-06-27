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

        paper = Paper(
            pmid=record.get("PMID", ""),
            doi=doi,
            title=record.get("TI", ""),
            authors=record.get("AU", []),
            journal=record.get("JT", ""),
            year=record.get("DP", "")[:4],
            abstract=record.get("AB", ""),
        )

        papers.append(paper)

    return papers
