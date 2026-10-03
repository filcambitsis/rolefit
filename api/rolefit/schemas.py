from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .normalization import FAMILIES


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    families: list[str] = Field(default_factory=list, max_length=5)
    countries: list[str] = Field(default_factory=list, max_length=100)
    employment: list[Literal["full-time", "part-time", "internship"]] = Field(
        default_factory=lambda: ["full-time", "part-time", "internship"], min_length=1, max_length=3
    )
    workplace: Literal["any", "remote", "hybrid", "on-site"] = "any"
    search: str = Field(default="", max_length=200)

    @field_validator("families")
    @classmethod
    def valid_families(cls, values):
        if not set(values).issubset(FAMILIES):
            raise ValueError("Unknown role family")
        return list(dict.fromkeys(values))

    @field_validator("countries")
    @classmethod
    def valid_countries(cls, values):
        if any(len(v) != 2 or not v.isalpha() or v != v.upper() for v in values):
            raise ValueError("Use uppercase ISO two-letter country codes")
        return list(dict.fromkeys(values))


class DecisionInput(BaseModel):
    state: Literal["saved", "skipped", "none"]
