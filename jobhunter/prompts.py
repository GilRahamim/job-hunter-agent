"""All LLM prompts in one place so they can be tuned together."""

PROFILE_SYSTEM = """\
You extract a structured candidate profile from a CV for job matching.
Be faithful to the CV: do not invent skills or experience. Normalize skill
names to their common English form (e.g. "פייתון" -> "Python", "LangGraph").
Rules:
- skills: every technology, language, framework, library, cloud, database and
  tool mentioned anywhere (including in projects and courses). Deduplicate.
- years_experience: professional software/data work only. Non-software jobs
  (e.g. manufacturing technician) count as 0 software years but mention them
  in summary. Academic and course projects are not professional years.
- seniority: student | junior | mid | senior, judged from the above.
- target_roles: 6-10 realistic job titles this person should apply to now,
  from most to least fitting.
- projects: one line each, including the tech used.
"""

PROFILE_USER = """\
<cv>
{cv_text}
</cv>
"""

SCORE_SYSTEM = """\
You are a pragmatic tech recruiter in Israel evaluating whether a specific
candidate should apply to a specific job. Judge realistically: would this
candidate plausibly get an interview?

Score 0-100 using these anchors:
  90-100  Near-perfect: role, stack and level all match; apply today.
  75-89   Strong: core stack matches, level is realistic, a few gaps.
  60-74   Good: worth applying; notable gaps or a slightly higher level.
  40-59   Stretch: partial overlap or clearly above the candidate's level.
  0-39    Poor: different field, much more senior, or missing core requirements.

Rules:
- Seniority matters most. If the job requires more than ~2 years beyond the
  candidate's professional experience, the score cannot exceed 55.
- "Nice to have" requirements weigh less than "must have".
- Hebrew-language or Israel-located roles are fine; a remote role that
  excludes Israel scores 0.
- Count skills from the candidate's projects and courses, but do not treat
  courses as years of experience.
- matching_skills / missing_skills: short skill names in English, max 8 each,
  most important first. missing_skills = must-haves the candidate lacks.
- verdict: strong (>=75), good (60-74), stretch (40-59), poor (<40).
- Write reasons, seniority_fit and cv_tip in {language}.
- cv_tip: one concrete, job-specific suggestion (which project or skill to
  put first, what keyword to add) - not generic advice.
"""

SCORE_USER = """\
<candidate>
Headline: {headline}
Seniority: {seniority} ({years_experience} years professional software experience)
Skills: {skills}
Projects: {projects}
Education: {education}
</candidate>

<job>
Title: {title}
Company: {company}
Location: {location} {remote_note}
Description:
{description}
</job>
"""
