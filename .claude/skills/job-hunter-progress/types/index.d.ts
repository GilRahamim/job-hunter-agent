export type Phase = { number: number; total: number; title: string }
export type Tests = { passed: number; failed: number; errors: number }
export type LastRun = { finished: string; newJobs: number; strong: number; failedSources: number }

export type Progress = {
  phase: Phase | null
  tests: Tests | null
  lastRun: LastRun | null
}

declare module 'claude-code' {
  interface PluginState {
    'job-hunter-progress': { progress: Progress; isHidden: boolean }
  }
}
