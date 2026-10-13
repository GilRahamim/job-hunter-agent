"""Core data models: Job (collected), CandidateProfile (from CV), JobMatch (from LLM)."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field


@dataclass
class Job:
    source: str
    title: str
    company: str
    url: str
    location: str = ""
    description: str = ""
    is_remote: bool = False
    remote_region: str = ""          # e.g. "Worldwide", "USA only"
    date_posted: str | None = None   # ISO date

    @property
    def id(self) -> str:
        return hashlib.sha1(self.url.lower().encode("utf-8")).hexdigest()[:16]

    @property
    def dedupe_key(self) -> str:
        """Normalized "company|title" — catches the same role on several boards."""
        def norm(s: str) -> str:
            return re.sub(r"[^\w֐-׿]+", " ", s.lower()).strip()
        return f"{norm(self.company)}|{norm(self.title)}"

    def text(self) -> str:
        return f"{self.title}\n{self.company}\n{self.description}"


class CandidateProfile(BaseModel):
    name: str = ""
    headline: str = ""
    summary: str = ""
    years_experience: float = 0
    seniority: Literal["student", "junior", "mid", "senior"] = "junior"
    skills: list[str] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)

    def as_text(self) -> str:
        parts = [self.headline, self.summary, ", ".join(self.skills),
                 ", ".join(self.target_roles), "\n".join(self.projects)]
        return "\n".join(p for p in parts if p)


class JobMatch(BaseModel):
    score: int = Field(ge=0, le=100)
    verdict: Literal["strong", "good", "stretch", "poor"]
    seniority_fit: str = ""
    required_years: float | None = None
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    reasons: str = ""
    cv_tip: str = ""
