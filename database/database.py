import json
import sqlite3
from pathlib import Path
from datetime import datetime

from models import Paper, Evidence


class ResearchDatabase:

    def __init__(self, db_path="database/research_library.db"):

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

        self.create_tables()

    # ==========================================================
    # DATABASE INITIALIZATION
    # ==========================================================

    def create_tables(self):

        self._create_papers_table()

        self._create_evidence_table()

        self._create_search_history_table()

        self._create_projects_table()

    def _create_papers_table(self):

        cursor = self.connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS papers(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            source TEXT NOT NULL,

            source_id TEXT,

            pmid TEXT UNIQUE,

            doi TEXT UNIQUE,

            title TEXT NOT NULL,

            authors TEXT,

            journal TEXT,

            year TEXT,

            abstract TEXT,

            keywords TEXT,

            mesh_terms TEXT,

            publication_types TEXT,

            language TEXT,

            url TEXT,

            retrieved_at TEXT
        )
        """)

        self.connection.commit()

    def _create_evidence_table(self):

        cursor = self.connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidence(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            paper_id INTEGER UNIQUE,

            study_design TEXT,

            population TEXT,

            sample_size TEXT,

            country TEXT,

            intervention TEXT,

            comparator TEXT,

            primary_outcomes TEXT,

            secondary_outcomes TEXT,

            key_findings TEXT,

            limitations TEXT,

            conclusion TEXT,

            risk_of_bias TEXT,

            llm_provider TEXT,

            llm_model TEXT,

            extraction_prompt_version TEXT,

            raw_json TEXT,

            extracted_at TEXT,

            FOREIGN KEY(paper_id)
                REFERENCES papers(id)
        )
        """)

        self.connection.commit()

    def _create_search_history_table(self):

        cursor = self.connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            query TEXT,

            source TEXT,

            number_of_results INTEGER,

            searched_at TEXT
        )
        """)

        self.connection.commit()

    def _create_projects_table(self):

        cursor = self.connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            project_name TEXT,

            description TEXT,

            created_at TEXT
        )
        """)

        self.connection.commit()

    # ==========================================================
    # PAPER METHODS
    # ==========================================================

    def paper_exists(self, pmid=None, doi=None):

        cursor = self.connection.cursor()

        if pmid:

            cursor.execute(
                "SELECT id FROM papers WHERE pmid=?",
                (pmid,),
            )

            return cursor.fetchone() is not None

        if doi:

            cursor.execute(
                "SELECT id FROM papers WHERE doi=?",
                (doi,),
            )

            return cursor.fetchone() is not None

        return False

    def insert_paper(self, paper: Paper):

        if self.paper_exists(
            pmid=paper.pmid,
            doi=paper.doi,
        ):
            return self.get_paper_id(
                pmid=paper.pmid,
                doi=paper.doi,
            )

        cursor = self.connection.cursor()

        cursor.execute(
            """
            INSERT INTO papers(

                source,
                source_id,
                pmid,
                doi,
                title,
                authors,
                journal,
                year,
                abstract,
                keywords,
                mesh_terms,
                publication_types,
                language,
                url,
                retrieved_at

            )

            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                paper.source,
                paper.source_id,
                paper.pmid,
                paper.doi,
                paper.title,
                paper.author_string,
                paper.journal,
                paper.year,
                paper.abstract,
                json.dumps(paper.keywords),
                json.dumps(paper.mesh_terms),
                json.dumps(paper.publication_types),
                paper.language,
                paper.url,
                paper.retrieved_at or datetime.now().isoformat(),
            ),
        )

        self.connection.commit()

        return cursor.lastrowid

    def insert_many(self, papers):

        ids = []

        for paper in papers:

            ids.append(self.insert_paper(paper))

        return ids

    def get_paper_id(self, pmid=None, doi=None):

        cursor = self.connection.cursor()

        if pmid:

            cursor.execute(
                "SELECT id FROM papers WHERE pmid=?",
                (pmid,),
            )

        else:

            cursor.execute(
                "SELECT id FROM papers WHERE doi=?",
                (doi,),
            )

        row = cursor.fetchone()

        if row:

            return row["id"]

        return None

    def _row_to_paper(self, row) -> Paper:

        return Paper(
            id=row["id"],
            source=row["source"],
            source_id=row["source_id"],
            pmid=row["pmid"],
            doi=row["doi"],
            title=row["title"],
            authors=row["authors"].split(", ") if row["authors"] else [],
            journal=row["journal"],
            year=row["year"],
            abstract=row["abstract"],
            keywords=json.loads(row["keywords"]) if row["keywords"] else [],
            mesh_terms=json.loads(row["mesh_terms"]) if row["mesh_terms"] else [],
            publication_types=(
                json.loads(row["publication_types"]) if row["publication_types"] else []
            ),
            language=row["language"],
            url=row["url"],
            retrieved_at=row["retrieved_at"],
        )

    def _row_to_evidence(self, row) -> Evidence:

        return Evidence(
            id=row["id"],
            paper_id=row["paper_id"],
            study_design=row["study_design"],
            population=row["population"],
            sample_size=row["sample_size"],
            country=row["country"],
            intervention=row["intervention"],
            comparator=row["comparator"],
            primary_outcomes=(
                json.loads(row["primary_outcomes"]) if row["primary_outcomes"] else []
            ),
            secondary_outcomes=(
                json.loads(row["secondary_outcomes"])
                if row["secondary_outcomes"]
                else []
            ),
            key_findings=json.loads(row["key_findings"]) if row["key_findings"] else [],
            limitations=json.loads(row["limitations"]) if row["limitations"] else [],
            conclusion=row["conclusion"],
            risk_of_bias=row["risk_of_bias"],
            llm_provider=row["llm_provider"],
            llm_model=row["llm_model"],
            extraction_prompt_version=row["extraction_prompt_version"] or "v1",
            raw_json=row["raw_json"],
            extracted_at=row["extracted_at"],
        )

    def get_paper(self, paper_id):

        cursor = self.connection.cursor()

        cursor.execute(
            "SELECT * FROM papers WHERE id=?",
            (paper_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_paper(row)

    def get_all_papers(self):

        cursor = self.connection.cursor()

        cursor.execute("SELECT * FROM papers")

        return [self._row_to_paper(row) for row in cursor.fetchall()]

    # ==========================================================
    # EVIDENCE METHODS
    # ==========================================================

    def evidence_exists(self, paper_id):

        cursor = self.connection.cursor()

        cursor.execute(
            "SELECT id FROM evidence WHERE paper_id=?",
            (paper_id,),
        )

        return cursor.fetchone() is not None

    def get_evidence(self, paper_id: int):

        cursor = self.connection.cursor()

        cursor.execute(
            "SELECT * FROM evidence WHERE paper_id=?",
            (paper_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_evidence(row)

    def get_all_evidence(self):

        cursor = self.connection.cursor()

        cursor.execute("SELECT * FROM evidence")

        return [self._row_to_evidence(row) for row in cursor.fetchall()]

    def insert_evidence(self, evidence: Evidence):

        cursor = self.connection.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO evidence(

                paper_id,

                study_design,

                population,

                sample_size,

                country,

                intervention,

                comparator,

                primary_outcomes,

                secondary_outcomes,

                key_findings,

                limitations,

                conclusion,

                risk_of_bias,

                llm_provider,

                llm_model,

                extraction_prompt_version,

                raw_json,

                extracted_at

            )

            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                evidence.paper_id,
                evidence.study_design,
                evidence.population,
                evidence.sample_size,
                evidence.country,
                evidence.intervention,
                evidence.comparator,
                json.dumps(evidence.primary_outcomes),
                json.dumps(evidence.secondary_outcomes),
                json.dumps(evidence.key_findings),
                json.dumps(evidence.limitations),
                evidence.conclusion,
                evidence.risk_of_bias,
                evidence.llm_provider,
                evidence.llm_model,
                evidence.extraction_prompt_version,
                evidence.raw_json,
                evidence.extracted_at or datetime.now().isoformat(),
            ),
        )

        self.connection.commit()

    # ==========================================================
    # SEARCH HISTORY
    # ==========================================================

    def log_search(
        self,
        query,
        source,
        number_of_results,
    ):

        cursor = self.connection.cursor()

        cursor.execute(
            """
            INSERT INTO search_history(

                query,

                source,

                number_of_results,

                searched_at

            )

            VALUES(?,?,?,?)
            """,
            (
                query,
                source,
                number_of_results,
                datetime.now().isoformat(),
            ),
        )

        self.connection.commit()

    # ==========================================================
    # CLEANUP
    # ==========================================================

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self):

        self.connection.close()
