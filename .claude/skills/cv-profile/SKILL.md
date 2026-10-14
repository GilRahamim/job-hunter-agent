---
name: cv-profile
description: How the Job Hunter project reads the owner's CV (PDF/DOCX/TXT, Hebrew or English) and turns it into a structured CandidateProfile with an LLM, with caching by file hash and a no-LLM fallback. Use this whenever working on jobhunter/cv.py, jobhunter/llm.py, the profile-extraction prompt, the dashboard Profile tab, or when the extracted skills/seniority look wrong.
---

# CV → CandidateProfile

The profile is the "query" for the whole system: every job is scored against it. A thin or wrong profile silently ruins every score, so this step is worth getting right and checking by eye.

## Flow (`jobhunter/cv.py`)

```
find_cv() → newest file in cv/ with extension .pdf/.docx/.txt/.md (ignore README.md)
read_text(path) → plain text
cv_hash = sha256(file bytes)[:16]
if db.load_profile(cv_hash): return it          # cache hit — no LLM call
profile = extract_with_llm(text) or extract_heuristic(text)
apply overrides from config.yaml profile.overrides (optional)
db.save_profile(cv_hash, path.name, profile.model_dump())
return profile, cv_hash
```

`cv_hash` is passed through the pipeline and stored on each scored job so re-scoring happens when the CV changes (see `job-matching`).

## Reading the file
- PDF: `pypdf.PdfReader(path)`; join `page.extract_text()` for all pages. If the result is under ~200 characters the PDF is probably scanned/image-based — raise a clear error telling the owner to export the CV as a text PDF or DOCX (don't silently continue with an empty profile).
- DOCX: `docx.Document(path)` — paragraphs **and** table cells (many CV templates put skills in tables).
- Normalize whitespace; keep line breaks (section structure helps the LLM).
- Hebrew CVs: pypdf sometimes returns reversed Hebrew lines. The LLM copes with it, but if the profile looks garbled, try DOCX.

## LLM extraction
`jobhunter/llm.py`:
```python
from langchain.chat_models import init_chat_model

def get_llm(cfg) -> BaseChatModel | None:
    llm_cfg = cfg["llm"]
    if llm_cfg["provider"] == "none" or not _has_key(llm_cfg["provider"]):
        return None
    return init_chat_model(llm_cfg["model"], model_provider=llm_cfg["provider"],
                           temperature=llm_cfg.get("temperature", 0))
```
Keys come from `.env`: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`; `ollama` needs none. The provider package must be installed (`langchain-anthropic`, `langchain-openai`, `langchain-google-genai`, `langchain-ollama`) — list them in requirements with a comment that only the chosen one is needed.

Extraction: `llm.with_structured_output(CandidateProfile).invoke([system, user])`. Put the prompt in `jobhunter/prompts.py`:

```text
SYSTEM:
You extract a structured candidate profile from a CV for job matching.
Be faithful to the CV: do not invent skills or experience. Normalize skill
names to their common English form (e.g. "פייתון" -> "Python", "LangGraph").
Rules:
- skills: every technology, language, framework, library, cloud, database,
  tool and professional method mentioned anywhere (including in projects and
  courses). Hard skills only, no soft skills. Deduplicate.
- years_experience: professional work in the field of the candidate's target
  roles only. Work in an unrelated field (e.g. a manufacturing technician who
  now applies for software roles) counts as 0 years but is mentioned in
  summary. Academic and course projects are not professional years.
- seniority: student | junior | mid | senior, judged from the above.
- target_roles: 6-10 realistic job titles this person should apply to now,
  from most to least fitting.
- projects: one line each, including the tech used.
USER:
<cv>
{cv_text}
</cv>
```

Why these rules: the classic failure is the LLM inflating years by counting a non-software job or a degree as experience, which then makes "3+ years" jobs look like a fit. Another is missing skills that appear only inside project descriptions.

## Heuristic fallback (no LLM)
- skills: match the CV text against `jobhunter/skills_vocab.txt` (one skill per line, with aliases `python|פייתון|py`) using word-boundary regex, case-insensitive.
- years_experience: 0; seniority: "junior"; target_roles: from `config.yaml` `search.queries`.
- headline/summary: first 2 non-empty lines.
This keeps the system usable without an API key and gives tests a deterministic profile.

## Overrides
Support an optional block in `config.yaml` so the owner can correct the extraction without editing the CV:
```yaml
profile:
  overrides:
    add_skills: [FastAPI]
    remove_skills: []
    seniority: junior
```

## Check
`python -m jobhunter.cv` prints the profile as pretty JSON plus `cache: hit/miss`. Ask the owner to eyeball the skills list and target roles once — it is the cheapest quality gate in the whole project.
