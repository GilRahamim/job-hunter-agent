// Pure rules, kept apart from the hooks so tests can check them directly.

// .env and .env.local etc. — but not .env.example (meant to be read and edited)
export const ENV_FILE = /(^|[\\/])\.env(\.(?!example$)[^\\/]+)?$/i
// the SQLite DB and its WAL/journal siblings
export const JOBS_DB = /(^|[\\/])data[\\/]jobs\.db(-wal|-shm|-journal)?$/i
// the tailoring agent's source of truth
export const MASTER_CV = /(^|[\\/])cv[\\/]cv_master\.ya?ml$/i

const ENV_IN_CMD = /(^|[\s\\/'"=])\.env(?!\.example)(\.[\w-]+)?(?=$|[\s'";|&)])/i

/** Bash commands that would destroy the application history or leak secrets. */
const BASH_RULES: readonly { pattern: RegExp; reason: string }[] = [
  {
    pattern: /\b(rm|del|erase|rd|rmdir|remove-item|unlink|mv|move|move-item)\b[^|;&\n]*jobs\.db/i,
    reason: 'data/jobs.db holds the application history (statuses, notes). Do not delete or move it.',
  },
  {
    pattern: /(>|\bout-file\b|\bset-content\b)\s*[^|;&\n]*data[\\/]jobs\.db/i,
    reason: 'Overwriting data/jobs.db would erase the application history.',
  },
  {
    pattern: /\bdrop\s+table\b/i,
    reason: 'DROP TABLE on the jobs DB is blocked. For schema changes add a migration (see the job-storage skill).',
  },
  {
    pattern: /\bdelete\s+from\s+["'`]?(jobs|runs|tailored_cvs|profile)\b(?![^;]*\bwhere\b)/i,
    reason: 'DELETE without WHERE would wipe a whole table. Add a WHERE clause or ask the owner.',
  },
]

export type Verdict = { isBlocked: false } | { isBlocked: true; reason: string }

export const checkBash = (command: string): Verdict => {
  for (const rule of BASH_RULES) {
    if (rule.pattern.test(command)) {
      return { isBlocked: true, reason: rule.reason }
    }
  }
  const readsEnv = /\b(cat|type|get-content|gc|less|more|head|tail|bat|grep|findstr|sed|awk|cp|copy)\b/i.test(command)
  if (readsEnv && ENV_IN_CMD.test(command)) {
    return { isBlocked: true, reason: '.env holds API keys and must not be read or copied. Use .env.example for the variable names.' }
  }
  return { isBlocked: false }
}

export const checkFile = (tool: 'Read' | 'Edit' | 'Write', path: string, exists: boolean): Verdict => {
  if (ENV_FILE.test(path)) {
    return { isBlocked: true, reason: '.env holds API keys; it is off-limits to Claude. Edit it yourself, or read .env.example for the variable names.' }
  }
  if (tool !== 'Read' && JOBS_DB.test(path)) {
    return { isBlocked: true, reason: 'data/jobs.db is written only by the app (jobhunter/db.py), never edited directly.' }
  }
  // Creating the first draft is allowed (Phase 8 step 1); changing an existing one is the owner's call.
  if (tool !== 'Read' && MASTER_CV.test(path) && exists) {
    return {
      isBlocked: true,
      reason: 'cv/cv_master.yaml is the owner\'s source of truth for tailoring. Show the proposed change and ask the owner to apply it.',
    }
  }
  return { isBlocked: false }
}

export const isPython = (path: string): boolean => /\.pyi?$/i.test(path)
