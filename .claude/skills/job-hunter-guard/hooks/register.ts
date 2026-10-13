import type { Register } from 'claude-code'

import { checkBash, checkFile, isPython } from './rules'

export const register: Register = on => {
  let hasRuff: boolean | undefined // unknown until the first Python edit

  // 1. File guard: .env, the jobs DB, the master CV
  on('tool.call', { tool: ['Read', 'Edit', 'Write'] }, async ($, e, next) => {
    const exists = await $.fs.exists(e.file_path).catch(() => true)
    const verdict = checkFile(e.tool, e.file_path, exists)
    if (verdict.isBlocked) {
      return { deny: `${$.plugin.name}: ${verdict.reason}` }
    }

    const ran = await next(e)

    // 2. After a successful Python edit: ruff check (read-only, never rewrites the file)
    const isEdit = e.tool === 'Edit' || e.tool === 'Write'
    if (!isEdit || !isPython(e.file_path) || ran.deny !== undefined || ran.isError || hasRuff === false) {
      return ran
    }
    const lint = await $.process
      .run(['ruff', 'check', '--output-format', 'concise', '--quiet', e.file_path], { timeoutMs: 20_000 })
      .catch(() => undefined)
    if (lint === undefined) {
      hasRuff = false
      $.ui.status('ruff not found — pip install ruff')
      return ran
    }
    hasRuff = true
    const name = e.file_path.split(/[\\/]/).pop()
    const issues = lint.stdout.trim()
    if (lint.exitCode === 0 || issues === '') {
      $.ui.status(undefined)
      return ran
    }
    const count = issues.split('\n').length
    $.ui.status(`ruff: ${count} issue${count === 1 ? '' : 's'} in ${name}`)
    return { ...ran, context: [...(ran.context ?? []), `ruff found issues in ${e.file_path} — fix them:\n${issues.slice(0, 4000)}`] }
  }).catch(($, e, next) =>
    // hook skipped (failure or re-entry): pure check only, treating the file as existing (fail closed)
    next.called ? next(e) : checkFile(e.tool, e.file_path, true).isBlocked ? { deny: 'job-hunter-guard: protected file' } : next(e),
  )

  // 3. Bash guard
  on('tool.call', { tool: 'Bash' }, ($, e, next) => {
    const verdict = checkBash(e.command)
    return verdict.isBlocked ? { deny: `${$.plugin.name}: ${verdict.reason}` } : next(e)
  }).catch(($, e, next) => {
    // the hook was skipped (failure or re-entry): judge again with the pure rule, no $ calls
    if (next.called) return next(e)
    const verdict = checkBash(e.command)
    return verdict.isBlocked ? { deny: `job-hunter-guard: ${verdict.reason}` } : next(e)
  })
}
