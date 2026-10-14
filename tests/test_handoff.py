import pytest

from jobhunter import db, handoff
from jobhunter.config import ROOT
from jobhunter.models import Job
from jobhunter.users import create_user

CV = "Dana Levi\ndana@example.com\nJunior Python Developer\nBuilt a RAG chatbot with LangChain.\n"
JOB = Job("greenhouse", "Junior Python Developer", "Acme Ltd", "https://acme/jobs/1", location="Tel Aviv, Israel",
          description="We build APIs in Python and FastAPI. Docker is an advantage.")


@pytest.fixture
def user():
    """A user with a CV and one scored job, all inside the temp folder."""
    user = create_user("Dana", "cv.txt", CV.encode())
    row = JOB.to_dict()
    row.update(score=81, prescore=55, verdict="strong", scored_by="llm:test", reasons="Python fits",
               matching_skills=["Python"], missing_skills=["FastAPI"], cv_tip="Lead with the RAG project")
    db.upsert_jobs([row], db.db_path(user=user))
    db.save_profile("h", "cv.txt", {"name": "Dana Levi"}, db.db_path(user=user))
    return user


def test_brief_holds_job_analysis_cv_and_rules(user, tmp_path):
    brief = handoff.write_brief(JOB.id, user)
    text = brief.read_text(encoding="utf-8")
    assert brief.parent == tmp_path / "users" / user / "data" / "tailored" / f"acme-ltd-junior-python-developer-{JOB.id[:6]}"
    assert "# Application kit: Junior Python Developer at Acme Ltd" in text
    assert "You are helping Dana Levi apply" in text
    assert "FastAPI. Docker is an advantage." in text                       # the full posting
    assert "Missing skills: FastAPI" in text and "CV tip: Lead with the RAG project" in text
    assert "Built a RAG chatbot with LangChain." in text                     # the CV itself
    assert "Never add a skill, tool, employer" in text                       # the no-fabrication rule
    assert str(brief.parent) in text and "--docx" in text and "cv_tailored.md" in text
    assert "looks English" in text and "written in Hebrew" in text           # posting vs. prep language


def test_brief_for_heuristic_job_and_unknown_id(user):
    row = Job("remotive", "דרוש/ה מפתח/ת פייתון", "", "https://x/2", description="ניסיון בפייתון").to_dict()
    row.update(score=40, prescore=40, scored_by="heuristic")
    db.upsert_jobs([row], db.db_path(user=user))
    text = handoff.write_brief(row["id"], user).read_text(encoding="utf-8")
    assert "keyword pre-score only" in text and "looks Hebrew" in text
    with pytest.raises(handoff.HandoffError):
        handoff.write_brief("nope", user)


def test_master_cv_is_included_when_present(user, tmp_path):
    (tmp_path / "users" / user / "cv" / "cv_master.yaml").write_text("projects: [rag]\n", encoding="utf-8")
    text = handoff.write_brief(JOB.id, user).read_text(encoding="utf-8")
    assert "## Master CV" in text and "projects: [rag]" in text


def test_prompt_is_short_and_relative_inside_the_project():
    brief = ROOT / "data" / "tailored" / "acme-x-123456" / "brief.md"
    assert handoff.claude_prompt(brief) == "Read data/tailored/acme-x-123456/brief.md and follow its instructions."
    assert handoff.shell_command(brief).startswith('claude "Read data/')


def test_subscription_env_drops_api_keys():
    env = handoff.subscription_env({"ANTHROPIC_API_KEY": "k", "ANTHROPIC_AUTH_TOKEN": "t", "PATH": "/bin"})
    assert env == {"PATH": "/bin"}


def test_launch_on_windows_opens_claude_without_the_api_key(user, monkeypatch):
    calls = []
    monkeypatch.setattr(handoff, "claude_path", lambda: r"C:\tools\claude.exe")
    monkeypatch.setattr(handoff.subprocess, "Popen", lambda cmd, **kw: calls.append((cmd, kw)))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    brief = handoff.write_brief(JOB.id, user)
    handoff.launch_claude(brief, system="windows")
    cmd, kw = calls[0]
    assert cmd == [r"C:\tools\claude.exe", handoff.claude_prompt(brief)]
    assert "ANTHROPIC_API_KEY" not in kw["env"] and kw["cwd"] == ROOT


def test_launch_on_macos_uses_terminal_and_unsets_keys(user, monkeypatch):
    calls = []
    monkeypatch.setattr(handoff, "claude_path", lambda: "/usr/local/bin/claude")
    monkeypatch.setattr(handoff.subprocess, "Popen", lambda cmd, **kw: calls.append(cmd))
    handoff.launch_claude(handoff.write_brief(JOB.id, user), system="darwin")
    script = calls[0][2]
    assert calls[0][0] == "osascript" and "unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN" in script


def test_launch_without_claude_or_elsewhere_explains(user, monkeypatch):
    brief = handoff.write_brief(JOB.id, user)
    monkeypatch.setattr(handoff, "claude_path", lambda: None)
    with pytest.raises(handoff.HandoffError, match="not installed"):
        handoff.launch_claude(brief, system="windows")
    assert not handoff.can_launch("windows")
    monkeypatch.setattr(handoff, "claude_path", lambda: "/usr/bin/claude")
    with pytest.raises(handoff.HandoffError, match="open a terminal"):
        handoff.launch_claude(brief, system="linux")
    assert handoff.can_launch("windows") and not handoff.can_launch("linux")


def test_markdown_to_docx(tmp_path):
    from docx import Document

    md = tmp_path / "cv_tailored.md"
    md.write_text("# Dana Levi\n\n## Skills\n- **Python**, SQL\n- LangChain\n\n---\nBuilt things.\n"
                  "ניסיון בפייתון\n", encoding="utf-8")
    out = handoff.markdown_to_docx(md)
    doc = Document(out)
    texts = [(p.style.name, p.text) for p in doc.paragraphs]
    assert texts[:4] == [("Heading 1", "Dana Levi"), ("Heading 2", "Skills"),
                         ("List Bullet", "Python, SQL"), ("List Bullet", "LangChain")]
    assert doc.paragraphs[2].runs[0].bold is True
    assert doc.paragraphs[-1].paragraph_format.alignment == 2           # Hebrew line is right-aligned


def test_kit_files_lists_what_claude_wrote(user):
    brief = handoff.write_brief(JOB.id, user)
    (brief.parent / "cover_letter.md").write_text("Dear Acme", encoding="utf-8")
    assert [p.name for p in handoff.kit_files(brief.parent)] == ["cover_letter.md"]


def test_cli_list_and_brief(user, capsys, monkeypatch):
    assert handoff.main(["--list", "--user", user]) == 0
    assert JOB.id in capsys.readouterr().out
    assert handoff.main([JOB.id, "--user", user]) == 0
    out = capsys.readouterr().out
    assert "brief:" in out and 'claude "Read' in out
    assert handoff.main(["missing", "--user", user]) == 1
