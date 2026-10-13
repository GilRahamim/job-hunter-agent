import { describe, expect, test } from 'claude-code/testing'
import type { On } from 'claude-code'

import { parsePlan, parsePytest, readLastRun, readPhaseNumber, toPhase } from './parse'

const PLAN_MD = `# Plan
## Phase 0 — Project skeleton
## Phase 4 — Filtering and matching
## Phase 8 — CV Tailoring Agent
`
const RUN = { finished: '2026-10-13T06:31:02+00:00', newJobs: 37, strong: 5, failedSources: 1 }

// Beneath the plugin: files, python, and the shell.
const engine = (on: On, files: Record<string, string>, opts: { pytest?: string; db?: boolean } = {}) => {
  const written: Record<string, string> = {}
  const toasts: string[] = []
  on('fs.read', ($, e) => {
    const key = Object.keys({ ...files, ...written }).find(k => e.path.replace(/\\/g, '/').endsWith(k))
    return key === undefined ? { deny: 'ENOENT' } : { value: written[key] ?? files[key] ?? '' }
  })
  on('fs.write', ($, e) => {
    written['.claude/phase.json'] = e.text
    return { value: undefined }
  })
  on('process.run', () => ({
    value: { exitCode: 0, stdout: opts.db === false ? 'null' : JSON.stringify(RUN), stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
  }))
  on('command.register', ($, e) => ({ value: { command: e.name } }))
  on('ui.toast', ($, e) => {
    toasts.push(String((e as { text?: unknown }).text ?? e))
    return { value: undefined }
  })
  on('tool.call', () => ({ result: {} as never, text: opts.pytest ?? '' }))
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('ui.render', ($, e) => {
    const { Box } = $.ui.resolve(e)
    return <Box key="engine-default" /> // the engine's own band: empty
  })
  return { written, toasts }
}

describe('parsing', () => {
  test('plan, phase file, pytest summary, last run', () => {
    const phases = parsePlan(PLAN_MD)
    expect(toPhase(phases, 4)).toEqual({ number: 4, total: 8, title: 'Filtering and matching' })
    expect(readPhaseNumber('{"phase": 3}')).toBe(3)
    expect(readPhaseNumber('garbage')).toBeNull()
    expect(parsePytest('....\n23 passed, 1 failed in 0.41s')).toEqual({ passed: 23, failed: 1, errors: 0 })
    expect(parsePytest('= 2 failed, 10 passed, 1 error in 3s =')).toEqual({ passed: 10, failed: 2, errors: 1 })
    expect(parsePytest('nothing here')).toBeNull()
    expect(readLastRun(JSON.stringify(RUN))?.strong).toBe(5)
    expect(readLastRun('null')).toBeNull()
  })
})

describe('band', () => {
  for (const surface of ['terminal', 'desktop'] as const) {
    test(`shows phase, tests and last run on ${surface}`, async ($, on) => {
      engine(on, { 'docs/IMPLEMENTATION_PLAN.md': PLAN_MD, '.claude/phase.json': '{"phase": 4}' }, { pytest: '23 passed in 0.4s' })
      await $.session.start({ cwd: '/proj', surface: 'terminal', isInteractive: true })
      await $.tool.call({ tool: 'Bash', command: 'pytest -q' } as never)
      const ui = await $.ui.mount({ plugin: 'job-hunter-progress', surface, component: 'AbovePrompt', props: { hasSurvey: false } as never })
      expect((await ui.find({ text: /Phase 4\/8/ }))).toBeDefined()
      expect((await ui.find({ text: /23 passed/ }))).toBeDefined()
      expect((await ui.find({ text: /37 new, 5 strong/ }))).toBeDefined()
      await ui.press({ key: 'hide' })
      expect(await ui.find({ text: /Phase 4/ })).toBeUndefined()
    })
  }

  test('/phase writes the phase file', async ($, on) => {
    const { written } = engine(on, { 'docs/IMPLEMENTATION_PLAN.md': PLAN_MD })
    await $.session.start({ cwd: '/proj', surface: 'terminal', isInteractive: true })
    const r = await $.command.run({ command: 'phase', args: '8' } as never)
    expect(JSON.parse(written['.claude/phase.json'] ?? '{}')).toEqual({ phase: 8 })
    expect(JSON.stringify(r)).toMatch(/Phase 8\/8/)
  })

  test('failing tests raise a toast', async ($, on) => {
    const { toasts } = engine(on, { 'docs/IMPLEMENTATION_PLAN.md': PLAN_MD }, { pytest: '2 failed, 5 passed in 1s' })
    await $.session.start({ cwd: '/proj', surface: 'terminal', isInteractive: true })
    await $.tool.call({ tool: 'Bash', command: 'pytest' } as never)
    expect(toasts.join(' ')).toMatch(/2 failing/)
  })
})

