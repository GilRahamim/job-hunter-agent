# Tailoring prompts

Put these in `jobhunter/tailor/prompts.py`. All calls use `with_structured_output(<Model>)`.

## ANALYZE_JOB → `JobRequirements`
```text
Extract what this job actually requires, for tailoring a CV.
- must_have: requirements stated as required / "you have" / minimum. Short skill or experience phrases.
- nice_to_have: "bonus", "advantage", "preferred", "יתרון".
- keywords: up to 25 exact terms and phrases as written in the posting (ATS matches literal text),
  e.g. "LLM", "RAG pipelines", "Python", "production ML systems".
- seniority and years required, if stated.
- domain: the company's product area in 3-6 words.
- language: language the posting is written in.
<job>{title} at {company}
{description}</job>
```

## REWRITE → `TailoredCV`
```text
You tailor a CV for one specific job. You may ONLY use facts from the provided master CV content.

Hard rules:
1. Do not add any skill, tool, employer, title, date, number, degree or project that is not in the
   source content. If the job asks for something the candidate lacks, leave it out.
2. Every bullet you write must list source_ids: the ids of the master bullets it is based on.
3. Rephrasing is allowed and encouraged: use the job's terminology where the source genuinely supports it.
4. Keep the candidate's skill levels: never present a "familiar" skill as a core strength.
5. Summary: 3 lines, specific to this role and domain, no clichés ("passionate", "team player").
6. Bullets: start with a strong verb, say what was built, with what, and the result. Max 2 lines each.
7. Order skills so that ones matching the job's must-haves come first.
{feedback_block}

<job_requirements>{requirements_json}</job_requirements>
<selected_content>{selection_json}</selected_content>
```
`{feedback_block}` on retry:
```text
Your previous draft contained unsupported claims. Remove or fix exactly these, without adding anything new:
{violations}
```

## VERIFY (LLM judge) → `list[BulletCheck]`
```text
For each tailored bullet, check it against its source bullets. A claim is supported only if the
source states it or it is a direct rewording. Technologies, numbers, scope ("led", "production",
"team of 5") and outcomes must all be in the source.
Return for each bullet: supported (true/false) and, if false, the exact unsupported phrase.
<pairs>{bullets_with_sources_json}</pairs>
```
Use a different (or the same, temperature 0) model than `rewrite`; a judge is more reliable when it only checks.

## COVER_LETTER → text
```text
Write a cover letter (150-220 words, {language}) for this job using only facts from the tailored CV.
Open with why this specific role/company (use one concrete detail from the posting), then 2 short
evidence paragraphs mapping the candidate's most relevant work to the top requirements, then a
one-line close. No flattery, no clichés, no claims beyond the CV.
```

## MASTER_DRAFT (bootstrap) → `MasterCV`
```text
Convert this CV into the master-CV structure. Split each role and project into atomic bullets
(one achievement each) and tag each bullet with the skills it demonstrates. Do not invent anything;
where information is missing, leave the field empty. Mark every skill level as "strong" unless the
CV indicates otherwise — the candidate will correct levels manually.
<cv>{cv_text}</cv>
```
