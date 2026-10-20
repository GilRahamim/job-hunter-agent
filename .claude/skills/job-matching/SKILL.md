---
name: job-matching
description: Filtering and scoring logic for the Job Hunter project — location rules (Israel incl. Hebrew city names, remote-region eligibility), role and seniority filters, the TF-IDF + skill-overlap pre-score, parallel LLM scoring with structured JobMatch output, the scoring prompt and calibration rubric, and re-scoring on CV change. Use this whenever touching jobhunter/filters.py, jobhunter/matcher.py, jobhunter/prompts.py or skills_vocab.txt, or when scores look too high/low, irrelevant jobs get through, or good jobs get filtered out.
---

# Filtering and matching

Three stages, cheapest first, so the LLM only sees jobs that already look plausible:

1. **filter** (rules, free) → 2. **prescore** (TF-IDF + skills, free) → 3. **LLM score** (top N only)

All thresholds and keyword lists come from `config.yaml` (`filters`, `matching`). Do not hard-code them.

## 1. Filters — `filters.py`

Implement each rule as a small pure function returning `(keep: bool, reason: str)` and record the drop reason. Logging per-reason counts (`dropped: location=812, role=301, senior=97, age=40`) is what makes tuning possible.

**Location** — keep if `is_israel(job)` or `remote_ok(job)`:
- `is_israel`: regex over `location` (and `remote_region`) — English and Hebrew. Full pattern in `references/patterns.md`. Include `Israel`, `IL` as a standalone token, major cities and tech hubs (Tel Aviv, Herzliya, Haifa, Jerusalem, Petah Tikva, Ramat Gan, Ra'anana, Netanya, Rehovot, Yokneam, Kiryat Gat, Beer Sheva, Caesarea, Hod Hasharon, Kfar Saba, Modiin, Rosh HaAyin, Ness Ziona, Rishon LeZion, Holon, Or Yehuda, Airport City, Petah Tikva variants) and their Hebrew names.
- `remote_ok`: job is remote **and** its region is acceptable. Acceptable = empty region, or contains any of `config.filters.remote_regions_ok` (worldwide, anywhere, EMEA, Europe, Israel…). Reject explicit restrictions that exclude Israel: `US only`, `USA`, `United States`, `Canada`, `LATAM`, `UK only`, `APAC`, and timezone-only restrictions like `US timezones`. A Himalayas `locationRestrictions` list is acceptable only if empty or it includes Israel.
- A job whose `location` is a non-Israeli city and is not remote → drop.

**Role** — title (lower-cased, padded with spaces so `" ai "` works) contains any `role_keywords` and none of `exclude_keywords` — unless it also has an `exclude_exceptions` word (`" noc "`, `" soc "`, `secops`), so "NOC Technician" stays while "Field Technician" goes (`filters.excluded_title`).

**Seniority** — if `exclude_senior`, drop titles containing `senior_keywords`. Note `"lead"` also matches "Leading"… use word boundaries (`\blead\b`). Titles like "Software Engineer II" are fine; "III"/"IV" lean senior — leave them for the LLM.

**LLM backstop** — the scoring prompt asks for `required_years`; `agent.save_node` does not save a new job whose LLM reading is over `filters.years_over_limit` (reason `experience_llm`), and `db.not_junior_ids` hides stored ones in the dashboard. When the rules miss a phrasing, add it to `required_years` with a test (Hebrew number words and "YOE" were added this way).

**Age** — drop if `date_posted` older than `max_age_days`; keep when unknown.

## 2. Pre-score — `matcher.prescore(profile, jobs) -> list[float]`

$$
\text{prescore} = 100\cdot\Big(0.6\cdot \tilde{s}_{\text{tfidf}} + 0.4\cdot \frac{|K_{\text{cv}} \cap K_{\text{job}}|}{\max(1,\,|K_{\text{job}}|)}\Big) - \text{penalty}
$$

- TF-IDF: fit `TfidfVectorizer(ngram_range=(1,2), min_df=1, sublinear_tf=True, stop_words="english")` on `[profile.as_text()] + [job.text() for job in jobs]`; cosine of each job vs the profile; min–max normalize across the batch (raw cosines are small and batch-dependent).
- Skills: extract $K_{\text{job}}$ from title + description with the same `skills_vocab.txt` matcher used by `cv-profile`. A starter vocabulary (~140 skills with Hebrew aliases) is in `assets/skills_vocab.txt` — copy it to `jobhunter/skills_vocab.txt`. Escape aliases with `re.escape` and use `(?<![\w+#.])alias(?![\w+#])` boundaries so `C++`, `C#`, `.NET` and `Go` match correctly (plain `\b` fails on `+`/`#`; and single-letter `C`/`R` need care — require them to appear in a comma/slash-separated list or next to "language"). Hebrew attaches one-letter prefixes ("בפייתון", "ופייתון"), so for aliases written in Hebrew allow an optional prefix: `(?<![\w])[בהולמשכ]?` + alias. Cap $|K_{\text{job}}|$ at ~15 in the denominator so long postings that list everything aren't over-penalized.
- Penalty: regex for required years (`(\d+)\+?\s*(years|yrs|שנות|שנים)`) — if the max stated requirement exceeds `profile.years_experience + 2`, subtract `min(25, 5 * gap)`.
- Return values clipped to `[0, 100]`.

This is a ranking signal, not a final answer — it only needs to put good jobs above bad ones.

## 3. LLM scoring — `matcher.llm_score(llm, profile, jobs) -> list[JobMatch | None]`

- Take jobs with `prescore >= min_prescore_for_llm`, sort desc, keep `llm_top_n`.
- `structured = llm.with_structured_output(JobMatch)`; call via `ThreadPoolExecutor(max_workers=cfg.llm.max_workers)`.
- Truncate the job description to ~6,000 characters (requirements usually come early; this bounds cost).
- Retry each call up to 3 times with backoff on rate-limit / validation errors; on final failure return `None` and keep the prescore. Never let one bad response fail the batch.
- Explanations (`reasons`, `seniority_fit`, `cv_tip`) are written in `config.profile.explanation_language` (default Hebrew); skill names stay in English.
- Learning from the user: once they have marked jobs, `choices_text(db.status_examples(matching.feedback_examples))` appends a `<candidate_choices>` block (`prompts.CHOICES_BLOCK`) to every scoring prompt and to the agent's `get_profile`: up to N jobs they pursued (interested/applied/interview/offer) and N they marked not relevant, newest first. It is a hint, not a rule; `rejected` (the company said no) is not a preference and is left out. `feedback_examples: 0` turns it off.
- `profile.preferences` (free text) goes into the same prompts as a `<candidate_preferences>` block (`prompts.PREFERENCES_BLOCK`, `matcher.preferences_text`): the kinds of roles and employers the person is open to (banks, health funds, NOC/SOC). It must not relax the anchors; `personalize` clears it for `auto_from_cv` users.

The prompt and the calibration rubric are in **`references/scoring-prompt.md`** — read it before changing the prompt. The rubric matters more than the wording: without anchors, models cluster everything at 70–85 and the ranking becomes useless.

## Final score
`score = match.score if match else prescore`, `scored_by = "llm:<model>" | "heuristic"`. Store `cv_hash` with each scored job.

## Re-scoring
When `rescore_on_cv_change` is true and the current `cv_hash` differs from a stored job's, the pipeline re-runs stages 2–3 on those jobs (excluding status `rejected`/`not_relevant`), still bounded by `llm_top_n` per run so a CV change doesn't trigger hundreds of LLM calls at once.

## Tuning checklist (when results look wrong)
- Many irrelevant jobs → check the drop-reason counts; tighten `role_keywords` / add `exclude_keywords`.
- Good jobs missing → search the DB/raw collection for them and see which filter dropped them.
- Scores all similar → the rubric anchors were removed or the description was truncated to almost nothing.
- Senior jobs scoring high → check `profile.years_experience` (cv-profile skill); the LLM trusts it.
