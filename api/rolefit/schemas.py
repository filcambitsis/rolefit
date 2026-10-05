from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .normalization import FAMILIES


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    families: list[str] = Field(default_factory=list, max_length=len(FAMILIES))
    employment: list[Literal["full-time", "part-time", "internship"]] = Field(
        default_factory=lambda: ["full-time", "part-time", "internship"], min_length=1, max_length=3
    )
    career_levels: list[Literal["junior", "mid", "senior", "lead", "unknown"]] = Field(
        default_factory=list, max_length=5
    )
    workplace: Literal["any", "remote", "hybrid", "on-site"] = "any"
    search: str = Field(default="", max_length=200)

    @field_validator("families")
    @classmethod
    def valid_families(cls, values):
        if not set(values).issubset(FAMILIES):
            raise ValueError("Unknown role family")
        return list(dict.fromkeys(values))

    @model_validator(mode="before")
    @classmethod
    def drop_legacy_country_preference(cls, values):
        # Old browser sessions can still send countries. The app now always searches NL.
        if isinstance(values, dict):
            cleaned = {key: value for key, value in values.items() if key != "countries"}
            if isinstance(cleaned.get("career_levels"), list):
                cleaned["career_levels"] = [
                    level for level in cleaned["career_levels"] if level != "internship"
                ]
            return cleaned
        return values


class DecisionInput(BaseModel):
    state: Literal["saved", "skipped", "none"]
