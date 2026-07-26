export const MANUAL_RETURN_KEY = 'hksi.manualReturn'
export const EXAM_RESULT_KEY = 'hksi.examResult'

export interface ManualReturnState {
  path: string
  label: string
  /** Optional focus target after return (e.g. question id). */
  focusId?: string
}

export function saveManualReturn(state: ManualReturnState): void {
  try {
    sessionStorage.setItem(MANUAL_RETURN_KEY, JSON.stringify(state))
  } catch {
    /* ignore quota / private mode */
  }
}

export function readManualReturn(): ManualReturnState | null {
  try {
    const raw = sessionStorage.getItem(MANUAL_RETURN_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as ManualReturnState
    if (!data?.path || !data?.label) return null
    return data
  } catch {
    return null
  }
}

export function clearManualReturn(): void {
  try {
    sessionStorage.removeItem(MANUAL_RETURN_KEY)
  } catch {
    /* ignore */
  }
}

export function buildManualHref(
  path: string,
  returnState: ManualReturnState,
): string {
  saveManualReturn(returnState)
  const url = new URL(path, window.location.origin)
  url.searchParams.set('from', '1')
  return `${url.pathname}${url.search}`
}
