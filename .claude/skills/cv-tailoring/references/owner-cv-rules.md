# The owner's CV rules (from his "resume creator" Claude project)

The owner already tailors his CV by hand in a claude.ai Project with the `gil-cv-tailor` skill. Anything this repo produces for **the owner** — `/apply`, the headless auto-tailor, the Phase 8 graph — must give the same result, or he gets two different CVs for the same kind of job. These rules override the generic parts of `cv-tailoring` (notably the `template.docx` / docxtpl rendering) for the owner. Other users keep the generic behaviour.

Personal content is **not** in this file (the repo is on GitHub). It lives in the gitignored `cv/` folder (the notes in `cv/notes/`, because `find_cv()` reads every `.md` directly in `cv/` as a CV and the newest one wins):
- `cv/notes/master_cv.md` — the master CV as text, with its structure note and revision log (copy of the Project doc `claude/master-cv.md`).
- `cv/notes/experience_bank.md` — true facts the owner confirmed that are not in the CV, plus things he explicitly does **not** have (copy of `claude/experience-bank.md`).
- The original Word file in `cv/` (`Gil_Rahamim_Resume*.docx`) is the base of every tailored CV.

The claude.ai Project is the source of truth for those two docs; refresh the `cv/notes/` copies when they change there (their revision log has dates). Long-term plan: one source (`cv/cv_master.yaml`) that generates both.

## 1. Truth (absolute)
- Never invent experience, tools, years, titles, employers, degrees or metrics. Reword, reorder, select, emphasize only.
- Use experience-bank facts only when they fit the job, and with the wording the bank gives. Entries marked "scope unconfirmed" get conservative wording.
- The bank's **NOT** lines (tools he has not used, concepts he knows only in theory) are hard stops: never claim them, even as "familiar".
- No numbers until the bank's "Metrics" section has them.
- A must-have that neither source supports is a **gap**: list it in `changes.md` (unattended) or ask the owner (interactive). Facts he confirms go into the Project's experience bank, then the `cv/notes/` copy.

## 2. Structure lock (his most important rule)
Start from a copy of the original `.docx` and edit text **inside existing runs/paragraphs**. Never regenerate the CV from Markdown or a template — that changes fonts, spacing, tabs and bullets. (So for the owner, `handoff --docx` from Markdown is a fallback/preview, not the deliverable.)

Locked: section set, order and headings (SUMMARY, EMPLOYMENT, EDUCATION, PROJECTS, TECHNICAL SKILLS, MILITARY SERVICE, LANGUAGES); name and contact lines; fonts, sizes, margins, tab stops, bullet style, spacing, date format; **page count (1)**; entry headers, dates and entry order; number of bullets per entry; number of skills lines and their category labels.

Allowed: the title line under the name (mirror the job title, only if true); the summary reworded in place at about the same length; bullets reworded with the job's terms for the same real work, and reordered inside one entry; items reordered inside a skills line, or swapped for a related true item from the bank, keeping the line length so it does not wrap; bold.

Needs his OK first (suggest in `changes.md`, don't do it): adding/removing a bullet, entry or project; swapping a project for one from the bank (the bank names which project replaces which for which role type).

## 3. ATS and bold
- Keep the posting's exact spelling of keywords; for key acronyms use both forms once, e.g. "Retrieval-Augmented Generation (RAG)".
- Bold posting keywords in the summary and bullets: about 1–2 per bullet, ~15–25 in total. Never whole sentences.
- To bold one word, split the run and copy the run's other properties to each part.

## 4. Editing pitfalls
- Match Technical Skills lines by the exact label **with the colon** ("Deep Learning:") — course bullets start with the same words.
- When reordering bullets, write all new texts in one pass, so a rewritten bullet is not matched and overwritten again.

## 5. Verify, then PDF
Convert the original and the result to PDF and compare: same sections and order, same page count, no extra wrapped line. Extract the text and check reading order (ATS proxy). Then the final PDF.
File names: `Gil_Rahamim_CV_<Company>_<Role>.docx` / `.pdf`.

## 6. Report (Hebrew, short) — goes into `changes.md`
Must/Nice keyword match before → after; keywords added or emphasized; remaining gaps and how to handle them; structural changes worth considering; one-line fit verdict (strong / reasonable / stretch) and why.

## 7. Tracking
The owner also keeps a tracker artifact in claude.ai (statuses: tailored, applied, screen, interview, assignment, offer, rejected, closed). The job DB has its own `STATUSES` (`new, interested, applied, interview, offer, rejected, not_relevant`). Do not write statuses from code — the owner sets them. If the two are ever synced, map `screen`/`assignment` → `interview`, `closed` → `not_relevant`, `tailored` → no change (shown by the kit files instead).
