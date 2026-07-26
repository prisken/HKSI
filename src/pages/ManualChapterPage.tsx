import { Fragment, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useManualChapter } from '../hooks/useManual'
import {
  clearManualReturn,
  readManualReturn,
  type ManualReturnState,
} from '../lib/navigation'
import type { ManualBlock } from '../types/manual'
import './ManualPage.css'

function BlockView({
  block,
  versionId,
}: {
  block: ManualBlock
  versionId: string
}) {
  if (block.type === 'h3') {
    return <h3 className="manual__h3">{block.text}</h3>
  }

  if (block.type === 'li') {
    return <div className="manual__li">{block.text}</div>
  }

  if (block.type === 'figure') {
    const src = block.src
      ? `/data/manual/${versionId}/${block.src}`
      : null
    return (
      <figure className={`manual__figure${block.kind === 'table' ? ' manual__figure--table' : ''}`}>
        {src ? (
          <a href={src} target="_blank" rel="noreferrer" className="manual__figure-link">
            <img src={src} alt={block.alt || block.caption} loading="lazy" />
          </a>
        ) : null}
        <figcaption>{block.caption}</figcaption>
      </figure>
    )
  }

  if (block.num) {
    return (
      <p className="manual__p manual__p--num" id={`para-${block.num}`}>
        <span className="manual__num">{block.num}</span>
        <span className="manual__p-body">{block.text}</span>
      </p>
    )
  }

  return <p className="manual__p">{block.text}</p>
}

export function ManualChapterPage() {
  const { chapterId } = useParams()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const sectionParam = params.get('section')
  const paraParam = params.get('para')
  const { chapter, meta, loading, error } = useManualChapter(chapterId)
  const [returnTo, setReturnTo] = useState<ManualReturnState | null>(null)

  useEffect(() => {
    setReturnTo(readManualReturn())
  }, [])

  const activeSection = useMemo(() => {
    if (!chapter) return null
    if (sectionParam) {
      return chapter.sections.find((s) => s.id === sectionParam) ?? chapter.sections[0] ?? null
    }
    return chapter.sections[0] ?? null
  }, [chapter, sectionParam])

  useEffect(() => {
    if (!chapter || !activeSection) return
    const targetId = paraParam ? `para-${paraParam}` : sectionParam ? `sec-${activeSection.id}` : null
    if (!targetId) return
    const el = document.getElementById(targetId) ?? document.getElementById(`sec-${activeSection.id}`)
    if (el) {
      window.setTimeout(() => {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' })
        el.classList.add('is-manual-focus')
        window.setTimeout(() => el.classList.remove('is-manual-focus'), 1800)
      }, 80)
    }
  }, [chapter, activeSection, sectionParam, paraParam])

  function goSection(id: string) {
    const next = new URLSearchParams(params)
    next.set('section', id)
    next.delete('para')
    setParams(next)
  }

  function goBackToSource() {
    const target = returnTo
    clearManualReturn()
    setReturnTo(null)
    if (target?.path) navigate(target.path)
  }

  if (loading) return <p className="page-status">載入章節…</p>
  if (error) return <p className="page-status page-status--err">{error}</p>
  if (!chapter || !meta) return null

  const chNum = chapter.number
  const prev = meta.chapters.find((c) => c.number === chNum - 1)
  const next = meta.chapters.find((c) => c.number === chNum + 1)

  return (
    <div className="manual manual--chapter">
      {returnTo ? (
        <div className="manual__return">
          <button type="button" className="manual__return-btn" onClick={goBackToSource}>
            ← {returnTo.label}
          </button>
          <span className="manual__return-note">閱讀後可返回剛才的題目／成績頁</span>
        </div>
      ) : null}

      <header className="manual__top">
        <Link to="/manual" className="back">
          ← 溫習手冊目錄
        </Link>
        <div className="manual__version-badge">
          <span className="manual__ver-label">v{meta.versionLabel}</span>
          <span className="manual__ver-date">更新至 {meta.updatedThroughLabel}</span>
        </div>
      </header>

      <div className="manual__layout">
        <aside className="manual__aside">
          <p className="manual__aside-label">本章小節</p>
          {chapter.nav.map((n) => (
            <button
              key={n.id}
              type="button"
              className={activeSection?.id === n.id ? 'is-active' : ''}
              onClick={() => goSection(n.id)}
            >
              {n.title}
            </button>
          ))}
          <div className="manual__aside-chapters">
            <p className="manual__aside-label">其他章節</p>
            {meta.chapters.map((c) => (
              <Link
                key={c.id}
                to={`/manual/${c.number}`}
                className={c.number === chNum ? 'is-active' : ''}
              >
                第 {c.number} 章
              </Link>
            ))}
          </div>
        </aside>

        <article className="manual__content">
          <header className="manual__chapter-head">
            <p className="manual__kicker">溫習手冊 · 第 {chapter.number} 章</p>
            <h1>{chapter.title}</h1>
          </header>

          {chapter.sections.map((sec) => (
            <section key={sec.id} id={`sec-${sec.id}`} className="manual__section">
              <h2>{sec.title}</h2>
              <div className="manual__prose">
                {sec.blocks.map((b, i) => (
                  <Fragment key={i}>
                    <BlockView block={b} versionId={meta.versionId} />
                  </Fragment>
                ))}
              </div>
            </section>
          ))}

          <nav className="manual__pager">
            {prev ? (
              <Link to={`/manual/${prev.number}`}>← 第 {prev.number} 章</Link>
            ) : (
              <span />
            )}
            {next ? <Link to={`/manual/${next.number}`}>第 {next.number} 章 →</Link> : <span />}
          </nav>
        </article>
      </div>
    </div>
  )
}
