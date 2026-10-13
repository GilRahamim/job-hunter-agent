import { describe, expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

import { checkBash, checkFile } from './rules'

// Beneath the plugin: a tool that always succeeds, a file system where only `existing` exists,
// and a ruff that reports one issue.
const engine = (on: On, existing: string[] = [], ruff: 'issue' | 'clean' | 'missing' = 'clean') => {
  const ran: string[] = []
  on('tool.call', ($, e) => {
    ran.push(e.tool)
    return { result: {} as never, text: 'ok' }
  })
  on('fs.exists', ($, e) => ({ value: existing.some(p => e.path.replace(/\\/g, '/').endsWith(p)) }))
  on('process.run', () => {
    if (ruff === 'missing') return { deny: 'spawn ruff ENOENT' }
    const stdout = ruff === 'issue' ? 'jobhunter/x.py:1:1: F401 `os` imported but unused' : ''
    return { value: { exitCode: ruff === 'issue' ? 1 : 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('ui.status', () => ({ value: undefined }))
  return ran
}

const call = ($: Engine, input: Record<string, unknown>) => $.tool.call(input as never)

describe('file guard', () => {
  test('blocks reading .env but allows .env.example', async ($, on) => {
    const ran = engine(on)
    expect((await call($, { tool: 'Read', file_path: 'C:\\proj\\.env' })).deny).toBeDefined()
    expect((await call($, { tool: 'Read', file_path: '/proj/.env.local' })).deny).toBeDefined()
    expect((await call($, { tool: 'Read', file_path: '.env.example' })).deny).toBeUndefined()
    expect(ran).toEqual(['Read'])
  })

  test('blocks writing the jobs DB but allows reading it', async ($, on) => {
    engine(on)
    expect((await call($, { tool: 'Write', file_path: 'data/jobs.db', content: '' })).deny).toBeDefined()
    expect((await call($, { tool: 'Read', file_path: 'data/jobs.db' })).deny).toBeUndefined()
  })

  test('master CV: first draft allowed, later edits blocked', async ($, on) => {
    engine(on, ['cv/cv_master.yaml'])
    const edit = await call($, { tool: 'Edit', file_path: 'cv/cv_master.yaml', old_string: 'a', new_string: 'b' })
    expect(edit.deny).toBeDefined()
    expect(edit.deny).toMatch(/source of truth/)
  })

  test('master CV draft can be created when missing', async ($, on) => {
    engine(on, [])
    expect((await call($, { tool: 'Write', file_path: 'cv/cv_master.yaml', content: 'x' })).deny).toBeUndefined()
  })
})

describe('ruff after python edits', () => {
  test('issues reach the model as context', async ($, on) => {
    engine(on, [], 'issue')
    const r = await call($, { tool: 'Write', file_path: 'jobhunter/x.py', content: 'import os' })
    expect(r.context?.join('\n')).toMatch(/F401/)
  })

  test('clean file adds nothing', async ($, on) => {
    engine(on, [], 'clean')
    const r = await call($, { tool: 'Edit', file_path: 'jobhunter/x.py', old_string: 'a', new_string: 'b' })
    expect(r.context ?? []).toEqual([])
  })

  test('missing ruff never breaks the edit', async ($, on) => {
    engine(on, [], 'missing')
    const r = await call($, { tool: 'Write', file_path: 'jobhunter/x.py', content: '' })
    expect(r.deny).toBeUndefined()
  })
})

describe('bash guard', () => {
  test('blocks destructive DB commands', async ($, on) => {
    const ran = engine(on)
    for (const command of [
      'rm data/jobs.db',
      'Remove-Item .\\data\\jobs.db',
      'sqlite3 data/jobs.db "DROP TABLE jobs"',
      'sqlite3 data/jobs.db "DELETE FROM jobs"',
      'echo "" > data/jobs.db',
      'cat .env',
      'Get-Content .env',
    ]) {
      expect((await call($, { tool: 'Bash', command })).deny).toBeDefined()
    }
    expect(ran).toEqual([])
  })

  test('allows ordinary commands', async ($, on) => {
    const ran = engine(on)
    for (const command of [
      'pytest -q',
      'python run_agent.py --dry-run',
      'sqlite3 data/jobs.db "DELETE FROM jobs WHERE id=\'x\'"',
      'cat .env.example',
      'grep -r "environment" docs/',
    ]) {
      expect((await call($, { tool: 'Bash', command })).deny).toBeUndefined()
    }
    expect(ran).toHaveLength(5)
  })
})

describe('rules', () => {
  test('pure checks', () => {
    expect(checkFile('Read', 'docs/.envoy.md', false).isBlocked).toBe(false)
    expect(checkFile('Edit', 'tests/data/jobs.db.bak', false).isBlocked).toBe(false)
    expect(checkBash('python -c "import os; print(os.environ)"').isBlocked).toBe(false)
  })
})
