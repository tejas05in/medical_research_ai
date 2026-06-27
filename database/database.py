import sqlite3
from pathlib import Path
from datetime import datetime
from models import Paper


class ResearchDatabase:

    def __init__(self, db_path="database/research_library.db"):

        self.db_path = Path(db_path)

        self.db_path.parent.mkdir(exist_ok=True)

        self.connection = sqlite3.connect(self.db_path)

        self.create_tables()

    def create_tables(self):

        cursor = self.connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS papers (

            pmid TEXT PRIMARY KEY,

            doi TEXT,

            title TEXT,

            authors TEXT,

            journal TEXT,

            year TEXT,

            abstract TEXT

        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            search_date TEXT,

            query TEXT,

            database_name TEXT,

            number_of_results INTEGER

        )
        """)

        self.connection.commit()

    def insert_paper(self, paper: Paper):

        if self.paper_exists(paper.pmid):
            return

        cursor = self.connection.cursor()

        cursor.execute(
            """

        INSERT OR REPLACE INTO papers

        VALUES (?,?,?,?,?,?,?)

        """,
            (
                paper.pmid,
                paper.doi,
                paper.title,
                paper.author_string,
                paper.journal,
                paper.year,
                paper.abstract,
            ),
        )

        self.connection.commit()

    def insert_many(self, papers):

        for paper in papers:

            self.insert_paper(paper)

    def get_all_papers(self):

        cursor = self.connection.cursor()

        cursor.execute("""

        SELECT *

        FROM papers

        """)

        return cursor.fetchall()

    def paper_exists(self, pmid):

        cursor = self.connection.cursor()

        cursor.execute(
            """

        SELECT COUNT(*)

        FROM papers

        WHERE pmid=?

        """,
            (pmid,),
        )

        return cursor.fetchone()[0] > 0

    def log_search(self, query: str, database_name: str, number_of_results: int):

        cursor = self.connection.cursor()

        cursor.execute(
            """
            INSERT INTO search_history
            (
                search_date,
                query,
                database_name,
                number_of_results
            )
            VALUES (?, ?, ?, ?)
            """,
            (datetime.now().isoformat(), query, database_name, number_of_results),
        )

        self.connection.commit()
