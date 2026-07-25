import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useManualMeta } from '../hooks/useManual'
import type { ManualExtra } from '../types/manual'
import './ManualPage.css'

export function ManualExtraPage() {
  const { extraId } = useParams()
  const { meta, loading: metaLoading, error: metaError } = useManualMeta()
  const [extra, setExtra] = useState<ManualExtra | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!meta || !extraId) {
      setLoading(metaLoading)
      return
    }
    const ref = meta.extras?.find((e) => e.id === extraId)
    if (!ref) {
      setError('找不到此附錄')
      setLoading(false)
      return
    }
    let cancelled = false
    fetch(`/data/manual/${meta.versionId}/${ref.file}`)
      .then(async (res) => {
        if (!res.ok) throw new Error('無法載入附錄')
        return res.json() as Promise<ManualExtra>
      })
      .then((data) => {
        if (cancelled) return
        setExtra(data)
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
  }, [meta, extraId, metaLoading])

  if (loading) return <p className="page-status">載入中…</p>
  if (error || metaError) return <p className="page-status page-status--err">{error || metaError}</p>
  if (!extra || !meta) return null

  return (
    <div className="manual">
      <header className="manual__top">
        <Link to="/manual" className="back">
          ← 溫習手冊目錄
        </Link>
        <div className="manual__version-badge">
          <span className="manual__ver-label">v{meta.versionLabel}</span>
          <span className="manual__ver-date">更新至 {meta.updatedThroughLabel}</span>
        </div>
      </header>
      <article className="manual__content manual__content--solo">
        <h1>{extra.title}</h1>
        {extra.updatedAtLabel ? <p className="manual__lead">{extra.updatedAtLabel}</p> : null}
        {extra.text.split(/\n+/).map((line, i) => (
          <p key={i}>{line}</p>
        ))}
      </article>
    </div>
  )
}
