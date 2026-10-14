"""Hand one job to Claude on the person's subscription (Claude Code or a claude.ai chat), not the API.

The search finds and scores jobs; for the one you want to apply to, Claude does the writing:
a tailored CV, a cover letter, interview prep and a list of what changed. This module writes
<data>/tailored/<job>/brief.md with the posting, the search agent's analysis, the CV and the rules
(prompts.HANDOFF_BRIEF), and can open Claude Code on it. Claude saves its files next to the brief.

  python -m jobhunter.handoff --list                    # best jobs and their ids
  python -m jobhunter.handoff <job_id>                  # write the brief, print how to start Claude
  python -m jobhunter.handoff <job_id> --launch         # ... and open Claude Code on it
  python -m jobhunter.handoff --docx <folder>/cv_tailored.md   # Markdown -> Word
  (add --user <name> for a user added in the dashboard)
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from jobhunter import db
from jobhunter.config import ROOT, active_user, load_config
from jobhunter.cv import CVError, find_cv, read_text
from jobhunter.matcher import explanation_language
from jobhunter.prompts import HANDOFF_BRIEF, HANDOFF_DOCX_NOTE, HANDOFF_FILES_NOTE

BRIEF = "brief.md"
MAX_DESCRIPTION_CHARS = 15000
# Claude Code prefers these over the subscription login, and the dashboard has .env loaded:
# drop them so the launched session runs on the Claude subscription.
API_KEY_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
_SLUG = re.compile(r"[^a-z0-9]+")
_HEBREW = re.compile(r"[֐-׿]")


class HandoffError(RuntimeError):
    """Something the person has to fix (unknown job, Claude Code not installed)."""


# ------------------------------------------------------------ paths

def tailored_dir(db_file: str | Path) -> Path:
    """Next to the user's jobs.db: data/tailored for the owner, users/<id>/data/tailored for others."""
    return Path(db_file).parent / "tailored"


def _slug(text: str, n: int) -> str:
    return _SLUG.sub("-", (text or "").lower()).strip("-")[:n].strip("-")


def job_folder(job: dict[str, Any], db_file: str | Path) -> Path:
    """ASCII folder name ("acme-junior-python-developer-3f9a1c"), safe on Windows command lines."""
    name = "-".join(p for p in (_slug(job["company"], 20), _slug(job["title"], 40), job["id"][:6]) if p)
    return tailored_dir(db_file) / name


def kit_files(folder: Path) -> list[Path]:
    """What Claude wrote for this job (everything but the brief), newest first."""
    if not folder.is_dir():
        return []
    files = [p for p in folder.iterdir() if p.is_file() and p.name != BRIEF]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


# ------------------------------------------------------------ the brief

def _language_of(text: str) -> str:
    letters = re.findall(r"[^\W\d_]", text)
    hebrew = sum(1 for ch in letters if _HEBREW.match(ch))
    return "Hebrew" if letters and hebrew / len(letters) > 0.3 else "English"


def _analysis(job: dict[str, Any]) -> str:
    score = f"Match score: {job['score'] or 0:.0f}/100"
    if not job.get("verdict"):
        return f"{score} (keyword pre-score only; no LLM review of this job yet)."
    lines = [f"{score}, verdict: {job['verdict']} ({job.get('scored_by') or ''})"]
    if job.get("reasons"):
        lines.append(f"Why: {job['reasons']}")
    if job.get("seniority_fit"):
        lines.append(f"Seniority fit: {job['seniority_fit']}")
    if job.get("matching_skills"):
        lines.append(f"Matching skills: {', '.join(job['matching_skills'])}")
    if job.get("missing_skills"):
        lines.append(f"Missing skills: {', '.join(job['missing_skills'])}")
    if job.get("cv_tip"):
        lines.append(f"CV tip: {job['cv_tip']}")
    return "\n".join(lines)


def _cv(cfg: dict[str, Any]) -> tuple[str, str, str]:
    """(CV file path, CV text, master CV block) for the brief."""
    try:
        path = find_cv(cfg["profile"]["cv_dir"])
        cv_file, cv_text = str(path), read_text(path)
    except CVError as e:
        return "(none)", f"(the CV could not be read: {e})", ""
    master = path.parent / "cv_master.yaml"
    block = ""
    if master.exists():
        block = ("\n## Master CV (the richer source; the same rule applies)\n\n```yaml\n"
                 f"{master.read_text(encoding='utf-8').strip()}\n```\n")
    return cv_file, cv_text, block


def docx_command(md_file: Path) -> str:
    """The exact command, with this Python (it has python-docx), so it works without an activated venv."""
    parts = [sys.executable, "-m", "jobhunter.handoff", "--docx", str(md_file)]
    return subprocess.list2cmdline(parts) if os.name == "nt" else shlex.join(parts)


def build_brief(job: dict[str, Any], cfg: dict[str, Any], profile: dict[str, Any] | None,
                folder: Path) -> str:
    cv_file, cv_text, master_block = _cv(cfg)
    name = (profile or {}).get("name") or cfg.get("display_name") or "the candidate"
    description = (job.get("description") or "(no description was collected; open the link)").strip()
    return HANDOFF_BRIEF.format(
        name=name, title=job["title"], company=job["company"],
        location=job.get("location") or job.get("remote_region") or ("Remote" if job.get("is_remote") else "-"),
        url=job.get("url") or "-", description=description[:MAX_DESCRIPTION_CHARS],
        posting_language=_language_of(f"{job['title']} {description}"),
        language=explanation_language(cfg),
        output_note=HANDOFF_FILES_NOTE.format(folder=folder),
        docx_note=HANDOFF_DOCX_NOTE.format(command=docx_command(folder / "cv_tailored.md")),
        analysis=_analysis(job), cv_file=cv_file, cv_text=cv_text, master_block=master_block)


def write_brief(job_id: str, user: str | None = None, db_file: str | Path | None = None) -> Path:
    """Write (or refresh) the brief for one stored job. Returns its path."""
    user = active_user() if user is None else user
    db_file = db.db_path(db_file, user)
    job = db.job_detail(job_id, db_file)
    if not job:
        raise HandoffError(f"no job with id {job_id!r} (python -m jobhunter.handoff --list shows the ids)")
    cfg = load_config(user)
    folder = job_folder(job, db_file)
    folder.mkdir(parents=True, exist_ok=True)
    latest = db.latest_profile(db_file)
    brief = folder / BRIEF
    brief.write_text(build_brief(job, cfg, latest["data"] if latest else None, folder), encoding="utf-8")
    return brief


# ------------------------------------------------------------ starting Claude

def claude_prompt(brief: Path) -> str:
    """Short on purpose (Windows command lines): everything else is in the brief."""
    try:
        where = brief.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        where = brief.resolve().as_posix()
    return f"Read {where} and follow its instructions."


def shell_command(brief: Path) -> str:
    """What to type in a terminal at the project folder."""
    return f'claude "{claude_prompt(brief)}"'


def subscription_env(env: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if env is None else env)
    for var in API_KEY_VARS:
        env.pop(var, None)
    return env


def claude_path() -> str | None:
    return shutil.which("claude")


def _system() -> str:
    return "windows" if os.name == "nt" else sys.platform


def can_launch(system: str | None = None) -> bool:
    """A new terminal window can be opened here (Windows or macOS) and Claude Code is installed."""
    return bool(claude_path()) and (system or _system()) in ("windows", "darwin")


def launch_claude(brief: Path, system: str | None = None) -> None:
    """Open Claude Code in a new terminal window on the brief, signed in with the subscription."""
    exe = claude_path()
    if not exe:
        raise HandoffError("Claude Code is not installed (see https://code.claude.com/docs); "
                           "or attach brief.md to a chat on claude.ai")
    prompt = claude_prompt(brief)
    system = system or _system()
    if system == "windows":
        subprocess.Popen([exe, prompt], cwd=ROOT, env=subscription_env(),
                         creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
    elif system == "darwin":
        line = (f"cd {shlex.quote(str(ROOT))} && unset {' '.join(API_KEY_VARS)} && "
                f"claude {shlex.quote(prompt)}")
        line = line.replace("\\", "\\\\").replace('"', '\\"')
        subprocess.Popen(["osascript", "-e", f'tell application "Terminal" to do script "{line}"',
                          "-e", 'tell application "Terminal" to activate'])
    else:
        raise HandoffError(f"open a terminal in {ROOT} and run: {shell_command(brief)}")


# ------------------------------------------------------------ Markdown -> Word

def _add_runs(paragraph: Any, text: str) -> None:
    """**bold** inside a line; everything else plain."""
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if part:
            paragraph.add_run(part).bold = bool(i % 2)


def _rtl(paragraph: Any) -> None:
    """Right-to-left paragraph for Hebrew lines."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement

    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph._p.get_or_add_pPr().append(OxmlElement("w:bidi"))


def markdown_to_docx(md_file: str | Path, docx_file: str | Path | None = None) -> Path:
    """A plain Word copy of a Markdown CV or letter: headings, bullets, **bold**, paragraphs."""
    from docx import Document
    from docx.shared import Pt

    md_file = Path(md_file)
    out = Path(docx_file) if docx_file else md_file.with_suffix(".docx")
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    for raw in md_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or re.fullmatch(r"[-*_]{3,}", line):
            continue
        heading = re.match(r"(#{1,3})\s+(.*)", line)
        bullet = re.match(r"[-*•]\s+(.*)", line)
        if heading:
            p = doc.add_heading(heading.group(2).replace("**", ""), level=len(heading.group(1)))
        elif bullet:
            p = doc.add_paragraph(style="List Bullet")
            _add_runs(p, bullet.group(1))
        else:
            p = doc.add_paragraph()
            _add_runs(p, line)
        if _HEBREW.search(line):
            _rtl(p)
    doc.save(out)
    return out


# ------------------------------------------------------------ CLI

def _list(user: str, n: int = 20) -> None:
    rows = [r for r in db.jobs_table(db.db_path(user=user)) if r["status"] not in ("rejected", "not_relevant")]
    rows.sort(key=lambda r: r["score"] or 0, reverse=True)
    for r in rows[:n]:
        print(f"{r['score'] or 0:5.1f}  {r['id']}  {r['title']} | {r['company']} | {r['status']}")
    if not rows:
        print("no jobs yet: run python run_agent.py first")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare one job for Claude (subscription, not API)")
    parser.add_argument("job_id", nargs="?", help="id of a stored job (see --list)")
    parser.add_argument("--list", action="store_true", help="show the best jobs and their ids")
    parser.add_argument("--launch", action="store_true", help="open Claude Code on the brief (Windows/macOS)")
    parser.add_argument("--docx", metavar="MD_FILE", help="convert a Markdown file to Word and exit")
    parser.add_argument("--user", default=None, help="a user added in the dashboard (default: the owner)")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    user = args.user if args.user is not None else active_user()

    if args.docx:
        print(markdown_to_docx(args.docx))
        return 0
    if args.list or not args.job_id:
        _list(user)
        return 0
    try:
        brief = write_brief(args.job_id, user)
        print(f"brief: {brief}\nstart Claude in {ROOT}:\n  {shell_command(brief)}\n"
              "or attach the brief to a new chat on claude.ai")
        if args.launch:
            launch_claude(brief)
            print("Claude Code opened in a new window.")
    except HandoffError as e:
        print(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
