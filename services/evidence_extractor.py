import json
import os

from dotenv import load_dotenv

from models import Paper
from models import Evidence

from services.llm.llm_service import LLMService

load_dotenv()


class EvidenceExtractor:

    def __init__(self):

        self.llm = LLMService()

    SYSTEM_PROMPT = """
            You are an expert epidemiologist.

            Your task is to extract structured evidence
            from biomedical research articles.

            Rules

            1. Use ONLY the title and abstract.

            2. Never infer missing information.

            3. Return null if unavailable.

            4. Return valid JSON matching the schema.

            Fields

            study_design

            population

            sample_size

            country

            intervention

            comparator

            primary_outcomes

            secondary_outcomes

            key_findings

            limitations

            conclusion

            risk_of_bias
            """

    def extract(
        self,
        paper: Paper,
        paper_id: int,
    ) -> Evidence:

        prompt = f"""
            Title

            {paper.title}

            Abstract

            {paper.abstract}
            """

        evidence = self.llm.structured_output(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            schema=Evidence,
        )

        evidence.paper_id = paper_id

        evidence.llm_provider = os.getenv(
            "LLM_PROVIDER",
            "unknown",
        )

        evidence.llm_model = os.getenv(
            "GEMINI_MODEL",
            os.getenv(
                "OPENAI_MODEL",
                "unknown",
            ),
        )

        evidence.raw_json = json.dumps(
            evidence.model_dump(),
            indent=2,
        )

        return evidence
