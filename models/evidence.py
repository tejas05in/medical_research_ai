from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """
    Structured evidence extracted from a biomedical publication.
    """

    # Database IDs
    id: Optional[int] = None

    paper_id: Optional[int] = None

    # Study information
    study_design: Optional[str] = None

    population: Optional[str] = None

    sample_size: Optional[Union[int, str]] = None

    country: Optional[str] = None

    intervention: Optional[str] = None

    comparator: Optional[str] = None

    # Outcomes
    primary_outcomes: list[str] = Field(default_factory=list)

    secondary_outcomes: list[str] = Field(default_factory=list)

    key_findings: list[str] = Field(default_factory=list)

    limitations: list[str] = Field(default_factory=list)

    conclusion: Optional[str] = None

    risk_of_bias: Optional[str] = None

    # Provenance
    llm_provider: Optional[str] = None

    llm_model: Optional[str] = None

    extraction_prompt_version: str = "v1"

    raw_json: Optional[str] = None

    extracted_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    model_config = {"validate_assignment": True}
