import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Progress } from '../types'
import {
  LAST_RUN_PY, PHASE_FILE, PLAN, isAgentRun, isPytest, parsePlan, parsePytest,
  readLastRun, readPhaseNumber, shortTime, toPhase,
} from './parse'

const EMPTY: Progress = { phase: null, tests: null, lastRun: null }
const progress = atom({ plugin: 'job-hunter-progress', key: 'progress' } as const, EMPTY)
const isHidden = atom({ plugin: 'job-hunter-progress', key: 'isHidden' } as const, false)

const readText = ($: EngineInterface, path: string) => $.fs.read(path).then(t => (typeof t === 'string' ? t : '')).catch(() => '')

const loadPhase = async ($: EngineInterface) => {
  const phases = parsePlan(await readText($, PLAN))
  const number = readPhaseNumber(await readText($, PHASE_FILE)) ?? 0
  return toPhase(phases, number)
}

// `python` on Windows, `python3` on Linux/macOS; first one that answers wins.
const loadLastRun = async ($: EngineInterface) => {
  for (const python of ['python', 'python3']) {
    const out = await $.process.run([python, '-c', LAST_RUN_PY], { timeoutMs: 15_000 }).catch(() => undefined)
    if (out !== undefined && out.exitCode === 0) return readLastRun(out.stdout)
  }
  return null
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'phase',
      description: 'Job Hunter: show or set the current build phase (/phase 4)',
    })
    const [phase, lastRun] = await Promise.all([loadPhase($), loadLastRun($)])
    await update($, progress, p => ({ ...p, phase, lastRun }))
    return next(e)
  })

  on('command.run', { command: 'phase' }, async ($, e) => {
    const arg = e.args.trim()
    if (arg === 'hide' || arg === 'show') {
      await update($, isHidden, () => arg === 'hide')
      return { text: arg === 'hide' ? 'Progress band hidden.' : 'Progress band shown.' }
    }
    if (arg !== '') {
      const n = Number(arg)
      if (!Number.isInteger(n) || n < 0) return { text: 'Usage: /phase <number> | /phase hide | /phase show' }
      await $.fs.write(PHASE_FILE, JSON.stringify({ phase: n }) + '\n')
    }
    const phase = await loadPhase($)
    await update($, progress, p => ({ ...p, phase }))
    if (phase === null) return { text: `No phases found in ${PLAN}.` }
    return { text: `Phase ${phase.number}/${phase.total}${phase.title ? ` — ${phase.title}` : ''}` }
  })

  // Watch pytest and agent runs that Claude starts.
  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny !== undefined) return ran

    if (isPytest(e.command)) {
      const tests = parsePytest(ran.text ?? '')
      if (tests !== null) {
        await update($, progress, p => ({ ...p, tests }))
        if (tests.failed + tests.errors > 0) $.ui.toast(`pytest: ${tests.failed + tests.errors} failing`)
      }
    }
    if (isAgentRun(e.command) && !/--dry-run/.test(e.command)) {
      const lastRun = await loadLastRun($)
      await update($, progress, p => ({ ...p, lastRun }))
      if (lastRun !== null && lastRun.strong > 0) $.ui.toast(`Agent run: ${lastRun.newJobs} new jobs, ${lastRun.strong} strong`)
    }
    return ran
  }).catch(($, e, next) => next(e)) // never get in the way of a shell command

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const p = await read($, progress)
    const hidden = await read($, isHidden)
    if (e.props.hasSurvey || hidden || (p.phase === null && p.tests === null && p.lastRun === null)) {
      return next(e)
    }
    const { Box, Text, Button } = $.ui.resolve(e)
    const t = p.tests
    const isRed = t !== null && t.failed + t.errors > 0

    return (
      <Box flexDirection="row" gap={1}>
        {p.phase !== null && (
          <Text bold>
            Phase {p.phase.number}/{p.phase.total}
            {p.phase.title ? ` · ${p.phase.title}` : ''}
          </Text>
        )}
        {t !== null && (
          <Text color={isRed ? 'red' : 'green'}>
            {isRed ? `· tests ${t.failed + t.errors} failing, ${t.passed} passed` : `· tests ${t.passed} passed`}
          </Text>
        )}
        {p.lastRun !== null && (
          <Text dimColor>
            · last run {shortTime(p.lastRun.finished)}: {p.lastRun.newJobs} new, {p.lastRun.strong} strong
            {p.lastRun.failedSources > 0 ? `, ${p.lastRun.failedSources} sources failed` : ''}
          </Text>
        )}
        <Button key="hide" label="Hide" onPress={() => update($, isHidden, () => true)} />
      </Box>
    )
  })
}
