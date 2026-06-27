from pathlib import Path
import pandas as pd
from models import Paper


class PaperExporter:

    def __init__(self, output_dir="outputs"):
        self.output_dir = Path(output_dir)

        self.csv_dir = self.output_dir / "csv"
        self.md_dir = self.output_dir / "markdown"
        self.json_dir = self.output_dir / "json"

        self.csv_dir.mkdir(parents=True, exist_ok=True)
        self.md_dir.mkdir(parents=True, exist_ok=True)
        self.json_dir.mkdir(parents=True, exist_ok=True)

    def export_csv(self, papers, filename="papers.csv"):

        df = pd.DataFrame(
            [
                {
                    "PMID": p.pmid,
                    "DOI": p.doi,
                    "Title": p.title,
                    "Authors": p.author_string,
                    "Journal": p.journal,
                    "Year": p.year,
                    "Abstract": p.abstract,
                }
                for p in papers
            ]
        )

        path = self.csv_dir / filename
        df.to_csv(path, index=False)

        return path

    def export_markdown(self, papers, filename="papers.md"):

        path = self.md_dir / filename

        with open(path, "w", encoding="utf-8") as f:

            f.write("# Literature Search Results\n\n")

            f.write("| PMID | Year | Journal | Title |\n")
            f.write("|------|------|---------|-------|\n")

            for p in papers:

                title = p.title.replace("|", " ")

                f.write(f"| {p.pmid} | {p.year} | {p.journal} | {title} |\n")

        return path

    def export_json(self, papers, filename="papers.json"):

        import json

        path = self.json_dir / filename

        with open(path, "w", encoding="utf-8") as f:

            json.dump([p.to_dict() for p in papers], f, indent=2)

        return path
