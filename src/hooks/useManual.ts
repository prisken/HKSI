import { useEffect, useState } from 'react'
import type { ManualChapter, ManualIndex, ManualMeta } from '../types/manual'

let indexCache: ManualIndex | null = null
let metaCache: ManualMeta | null = null
const chapterCache = new Map<string, ManualChapter>()

export function useManualMeta() {
  const [meta, setMeta] = useState<ManualMeta | null>(metaCache)
  const [index, setIndex] = useState<ManualIndex | null>(indexCache)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(!metaCache)

  useEffect(() => {
    if (metaCache && indexCache) return
    let cancelled = false
    ;(async () => {
      try {
        const idxRes = await fetch('/data/manual/index.json')
        if (!idxRes.ok) throw new Error('無法載入溫習手冊索引')
        const idx = (await idxRes.json()) as ManualIndex
        const metaRes = await fetch(`/data/manual/${idx.currentVersion}/meta.json`)
        if (!metaRes.ok) throw new Error('無法載入溫習手冊版本資料')
        const m = (await metaRes.json()) as ManualMeta
        if (cancelled) return
        indexCache = idx
        metaCache = m
        setIndex(idx)
        setMeta(m)
        setLoading(false)
      } catch (e) {
        if (cancelled) return
        setError(e instanceof Error ? e.message : '載入失敗')
        setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  return { meta, index, error, loading }
}

export function useManualChapter(chapterId: string | undefined) {
  const { meta, loading: metaLoading, error: metaError } = useManualMeta()
  const [chapter, setChapter] = useState<ManualChapter | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!chapterId || !meta) {
      setLoading(metaLoading)
      return
    }
    const key = `${meta.versionId}:${chapterId}`
    if (chapterCache.has(key)) {
      setChapter(chapterCache.get(key)!)
      setLoading(false)
      return
    }
    const summary = meta.chapters.find((c) => c.id === chapterId || String(c.number) === chapterId)
    if (!summary) {
      setError('找不到此章節')
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    fetch(`/data/manual/${meta.versionId}/${summary.file}`)
      .then(async (res) => {
        if (!res.ok) throw new Error('無法載入章節內容')
        return res.json() as Promise<ManualChapter>
      })
      .then((data) => {
        if (cancelled) return
        chapterCache.set(key, data)
        setChapter(data)
        setError(null)
        setLoading(false)
      })
      .catch((e: unknown) => {
        if (cancelled) return
        setError(e instanceof Error ? e.message : '載入失敗')
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [chapterId, meta, metaLoading])

  return { chapter, meta, error: error || metaError, loading: loading || metaLoading }
}
