---
name: apply
description: Prepare an application for one job from the Job Hunter database, on the person's Claude subscription — a tailored CV, a cover letter, interview prep and a list of changes and gaps, with nothing invented. Use when someone types /apply <job-id>, or asks to tailor their CV, write a cover letter or prepare for an interview for a specific job the search found.
argument-hint: "[job-id] [--user name]"
---

# Apply for one job

The search agent finds and scores jobs; this is where Claude does the writing for the one job the
person picked. All the instructions live in the brief that `jobhunter/handoff.py` writes, so the
dashboard button, the CLI and this skill produce the same result.

Arguments: `$ARGUMENTS`

1. **Find the job.** If no job id was given, list the best ones and ask which:
   `python -m jobhunter.handoff --list` (add `--user <name>` for a person added in the dashboard).
   Use the project's Python: `.venv\Scripts\python.exe` on Windows when that venv exists.
2. **Write the brief:** `python -m jobhunter.handoff <job-id>` (plus `--user <name>` if given).
   It prints the path of `brief.md`.
3. **Read the brief and follow it exactly.** It holds the posting, the search agent's analysis, the
   CV and the rules. The rule that matters most: use only facts from the CV; never add a skill,
   employer, date, number or project. When the brief and the person disagree, ask the person.
4. Save the documents into the brief's folder, run the `--docx` command it gives, and finish with
   the short summary it asks for.

**For the owner**, also follow `.claude/skills/cv-tailoring/references/owner-cv-rules.md` and use `cv/notes/master_cv.md` + `cv/notes/experience_bank.md` (only facts from these; the bank's NOT lines are never claimed).

**For the owner the brief already carries these rules**, the notes and the paragraph map of the original `.docx`: write `cv_edits.json` and run the `--apply-edits` command it gives, never a script of your own.

**Unattended** (`--unattended` in the arguments; `claude -p "/apply <id> --unattended"` from `handoff.run_headless`, see the `auto-tailor` skill): nobody can answer, so ask nothing. The only shell command allowed is `python -m jobhunter.handoff ...` (write the brief exactly as in step 2, with the project's Python); every other command is denied, so do not try alternatives. Write every gap and every "needs his OK" suggestion into `changes.md`, finish the files, and stop.

Do not edit code, `config.yaml`, `cv/cv_master.yaml` or the database while doing this. The job's
status (applied, interview…) is the person's to set in the dashboard.
