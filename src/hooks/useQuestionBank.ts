import { useEffect, useState } from 'react'
import type { QuestionBank } from '../types'

let cached: QuestionBank | null = null

export function useQuestionBank() {
  const [data, setData] = useState<QuestionBank | null>(cached)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(!cached)

  useEffect(() => {
    if (cached) return
    let cancelled = false
    fetch('/data/questions.json')
      .then(async (res) => {
        if (!res.ok) throw new Error(`無法載入題庫 (${res.status})`)
        return res.json() as Promise<QuestionBank>
      })
      .then((bank) => {
        if (cancelled) return
        cached = bank
        setData(bank)
        setLoading(false)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : '載入失敗')
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { data, error, loading }
}
