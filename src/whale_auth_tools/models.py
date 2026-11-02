"""Questionnaire request and response models."""

from datetime import datetime
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, model_validator

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class Position(str, Enum):
    PHD_STUDENT = "PhD student"
    POSTDOC = "Postdoc"
    PI = "PI"
    RESEARCH_ENGINEER = "Research engineer"
    SYSTEMS_DEVELOPER = "Systems developer"
    DATA_STEWARD = "Data steward"
    BIOINFORMATICIAN = "Bioinformatician"
    OTHER = "Other"


class SciLifeLabAffiliation(str, Enum):
    INFRASTRUCTURE_UNIT_STAFF = "Infrastructure unit staff"
    AFFILIATED_RESEARCH_GROUP_MEMBER = "Affiliated research group member"
    OTHER = "Other"


class PlannedUse(str, Enum):
    CHAT_AND_WRITING = "Chat and writing assistance"
    SOFTWARE_DEVELOPMENT = "Software development"
    RESEARCH_AND_DATA_ANALYSIS = "Research and data analysis"
    TEACHING_AND_TRAINING = "Teaching and training"
    EVALUATION_OR_TESTING = "Evaluation or testing"
    OTHER = "Other"


class QuestionnaireSubmission(BaseModel):
    """Answers used by the service-access approval workflow."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    organisation: ShortText
    positions: Annotated[list[Position], Field(min_length=1, max_length=8)]
    position_other: LongText | None = Field(default=None, alias="positionOther")
    scilifelab_affiliation: SciLifeLabAffiliation = Field(alias="scilifelabAffiliation")
    scilifelab_affiliation_other: LongText | None = Field(
        default=None, alias="scilifelabAffiliationOther"
    )
    planned_uses: Annotated[list[PlannedUse], Field(min_length=1, max_length=6)] = Field(
        alias="plannedUses"
    )
    planned_use_other: LongText | None = Field(default=None, alias="plannedUseOther")
    add_to_slack: bool = Field(alias="addToSlack")
    contact_email: EmailStr | None = Field(default=None, alias="contactEmail")
    altcha_payload: str | None = Field(default=None, alias="altchaPayload", exclude=True)

    @model_validator(mode="after")
    def validate_conditional_answers(self) -> "QuestionnaireSubmission":
        if Position.OTHER in self.positions and not self.position_other:
            raise ValueError("positionOther is required when positions includes Other.")
        if (
            self.scilifelab_affiliation is SciLifeLabAffiliation.OTHER
            and not self.scilifelab_affiliation_other
        ):
            raise ValueError(
                "scilifelabAffiliationOther is required when scilifelabAffiliation is Other."
            )
        if PlannedUse.OTHER in self.planned_uses and not self.planned_use_other:
            raise ValueError("plannedUseOther is required when plannedUses includes Other.")
        if self.add_to_slack and not self.contact_email:
            raise ValueError("contactEmail is required when addToSlack is true.")
        return self


class SubmissionAccepted(BaseModel):
    id: UUID
    submitted_at: datetime = Field(alias="submittedAt")
    status: str = "received"


class StoredSubmission(SubmissionAccepted):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    organisation: str
    positions: list[Position]
    position_other: str | None = Field(alias="positionOther")
    scilifelab_affiliation: SciLifeLabAffiliation = Field(alias="scilifelabAffiliation")
    scilifelab_affiliation_other: str | None = Field(alias="scilifelabAffiliationOther")
    planned_uses: list[PlannedUse] = Field(alias="plannedUses")
    planned_use_other: str | None = Field(alias="plannedUseOther")
    add_to_slack: bool = Field(alias="addToSlack")
    contact_email: EmailStr | None = Field(alias="contactEmail")


class QuestionnaireSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    positions: list[str]
    scilifelab_affiliations: list[str] = Field(alias="scilifelabAffiliations")
    planned_uses: list[str] = Field(alias="plannedUses")
    questions: dict[str, str]
    notes: dict[str, str]


def questionnaire_schema() -> QuestionnaireSchema:
    return QuestionnaireSchema(
        positions=[item.value for item in Position],
        scilifelabAffiliations=[item.value for item in SciLifeLabAffiliation],
        plannedUses=[item.value for item in PlannedUse],
        questions={
            "organisation": "Which university or organisation are you affiliated to?",
            "positions": "Which position(s) do you hold?",
            "scilifelabAffiliation": "How are you affiliated to SciLifeLab?",
            "plannedUses": "What do you plan to use the OpenLLM service for?",
            "addToSlack": "Would you like to join the SciLifeLab service-users Slack channel?",
        },
        notes={
            "positions": "Select all positions that apply.",
            "plannedUses": "Select all intended uses that apply.",
            "contactEmail": "Required only when the respondent wants a Slack invitation.",
            "other": "Selecting Other requires the matching free-text field.",
        },
    )
