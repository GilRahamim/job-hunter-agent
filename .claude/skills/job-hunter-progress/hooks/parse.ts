// Pure parsing, kept apart from the hooks so tests can check it directly.
import type { LastRun, Phase, Tests } from '../types'

export const PLAN = 'docs/IMPLEMENTATION_PLAN.md'
export const PHASE_FILE = '.claude/phase.json'

/** "## Phase 4 — Filtering and matching" → { 4: "Filtering and matching" } */
export const parsePlan = (markdown: string): Map<number, string> => {
  const phases = new Map<number, string>()
  for (const m of markdown.matchAll(/^##\s+Phase\s+(\d+)\s*[—–-]\s*(.+?)\s*$/gm)) {
    phases.set(Number(m[1]), m[2] ?? '')
  }
  return phases
}

export const toPhase = (phases: Map<number, string>, number: number): Phase | null => {
  if (phases.size === 0) return null
  const total = Math.max(...phases.keys())
  return { number, total, title: phases.get(number) ?? '' }
}

export const readPhaseNumber = (json: string): number | null => {
  try {
    const n = Number((JSON.parse(json) as { phase?: unknown }).phase)
    return Number.isInteger(n) && n >= 0 ? n : null
  } catch {
    return null
  }
}

/** Reads pytest's summary line: "23 passed, 1 failed, 2 errors in 0.41s" (any order). */
export const parsePytest = (output: string): Tests | null => {
  const lines = output.split('\n').filter(l => /\b(passed|failed|error|errors|no tests ran)\b/.test(l))
  const summary = lines.at(-1)
  if (summary === undefined) return null
  const n = (word: RegExp) => Number(summary.match(word)?.[1] ?? 0)
  return { passed: n(/(\d+) passed/), failed: n(/(\d+) failed/), errors: n(/(\d+) errors?\b/) }
}

export const isPytest = (command: string) => /\bpytest\b/.test(command)
export const isAgentRun = (command: string) => /\brun_agent\.py\b/.test(command)

/** Python run on the host to read the last finished run from data/jobs.db; prints JSON or "null". */
export const LAST_RUN_PY = `
import json, os, sqlite3
p = os.path.join("data", "jobs.db")
if not os.path.exists(p):
    print("null"); raise SystemExit
c = sqlite3.connect(p)
try:
    r = c.execute("SELECT id, started, finished, stats FROM runs WHERE finished IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
    if r is None:
        print("null"); raise SystemExit
    stats = json.loads(r[3] or "{}")
    strong = c.execute("SELECT COUNT(*) FROM jobs WHERE score >= 75 AND first_seen >= ?", (r[1],)).fetchone()[0]
    failed = c.execute("SELECT COUNT(*) FROM source_health WHERE run_id = ? AND error IS NOT NULL AND error != ''", (r[0],)).fetchone()[0]
    print(json.dumps({"finished": r[2], "newJobs": int(stats.get("new", 0)), "strong": strong, "failedSources": failed}))
except sqlite3.Error:
    print("null")
`

export const readLastRun = (stdout: string): LastRun | null => {
  try {
    const v = JSON.parse(stdout.trim()) as LastRun | null
    return v && typeof v.newJobs === 'number' ? v : null
  } catch {
    return null
  }
}

/** "2026-10-13T06:31:02+00:00" → "13/10 09:31" in Israel time */
export const shortTime = (iso: string): string => {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  try {
    const parts = new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Asia/Jerusalem', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
    }).formatToParts(d)
    const get = (t: string) => parts.find(p => p.type === t)?.value ?? ''
    return `${get('day')}/${get('month')} ${get('hour')}:${get('minute')}`
  } catch {
    return iso.slice(5, 16).replace('T', ' ') // no Intl/time zone data: "10-13 06:31" UTC
  }
}
