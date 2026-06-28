import json

from models import Paper
from models import Evidence

from config.llm_config import GEMINI_MODEL, LLM_PROVIDER, OPENAI_MODEL
from services.llm.llm_service import LLMService


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

        # Capture raw LLM output before adding provenance metadata
        evidence.raw_json = json.dumps(
            evidence.model_dump(
                exclude={
                    "id",
                    "paper_id",
                    "llm_provider",
                    "llm_model",
                    "extraction_prompt_version",
                    "raw_json",
                    "extracted_at",
                }
            ),
            indent=2,
        )

        evidence.paper_id = paper_id

        evidence.llm_provider = LLM_PROVIDER

        if LLM_PROVIDER == "openai":
            evidence.llm_model = OPENAI_MODEL
        elif LLM_PROVIDER == "gemini":
            evidence.llm_model = GEMINI_MODEL
        else:
            evidence.llm_model = "unknown"

        return evidence
