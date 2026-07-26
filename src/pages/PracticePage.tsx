import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { QuestionCard } from '../components/QuestionCard'
import { useQuestionBank } from '../hooks/useQuestionBank'
import { groupByChapter } from '../lib/exam'
import type { AnswerKey } from '../types'
import './PracticePage.css'

export function PracticePage() {
  const { data, loading, error } = useQuestionBank()
  const [params, setParams] = useSearchParams()
  const chapterParam = params.get('chapter')
  const activeChapter = chapterParam ? Number(chapterParam) : null
  const qidParam = params.get('qid')
  const revealParam = params.get('reveal') === '1'
  const selParam = params.get('sel') as AnswerKey | null

  const [cursor, setCursor] = useState(0)
  const [selected, setSelected] = useState<AnswerKey | null>(null)
  const [revealed, setRevealed] = useState(false)
  const [restored, setRestored] = useState(false)

  const groups = useMemo(() => (data ? groupByChapter(data.questions) : []), [data])
  const questions = useMemo(() => {
    if (!data) return []
    if (activeChapter == null) return data.questions
    return data.questions.filter((q) => q.chapter === activeChapter)
  }, [data, activeChapter])

  const current = questions[cursor] ?? null

  // Restore position from URL (e.g. after returning from study manual)
  useEffect(() => {
    if (!data || restored) return
    if (qidParam) {
      const idx = questions.findIndex((q) => q.id === qidParam)
      if (idx >= 0) setCursor(idx)
    }
    if (selParam && ['A', 'B', 'C', 'D'].includes(selParam)) setSelected(selParam)
    if (revealParam) setRevealed(true)
    setRestored(true)
    if (qidParam) {
      window.setTimeout(() => {
        document.getElementById(`q-${qidParam}`)?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        })
      }, 120)
    }
  }, [data, questions, qidParam, selParam, revealParam, restored])

  // Keep URL in sync so manual return can restore exact spot
  useEffect(() => {
    if (!current || !restored) return
    const next = new URLSearchParams()
    if (activeChapter != null) next.set('chapter', String(activeChapter))
    next.set('qid', current.id)
    if (revealed) next.set('reveal', '1')
    if (selected) next.set('sel', selected)
    const same =
      next.get('chapter') === params.get('chapter') &&
      next.get('qid') === params.get('qid') &&
      next.get('reveal') === params.get('reveal') &&
      next.get('sel') === params.get('sel')
    if (!same) setParams(next, { replace: true })
  }, [current, activeChapter, revealed, selected, restored, params, setParams])

  function selectChapter(ch: number | null) {
    setCursor(0)
    setSelected(null)
    setRevealed(false)
    setRestored(true)
    if (ch == null) setParams({})
    else setParams({ chapter: String(ch) })
  }

  function go(delta: number) {
    setCursor((c) => Math.min(questions.length - 1, Math.max(0, c + delta)))
    setSelected(null)
    setRevealed(false)
  }

  if (loading) return <p className="page-status">載入題庫中…</p>
  if (error) return <p className="page-status page-status--err">{error}</p>
  if (!data) return null

  const returnPath = (() => {
    const p = new URLSearchParams()
    if (activeChapter != null) p.set('chapter', String(activeChapter))
    if (current) p.set('qid', current.id)
    p.set('reveal', '1')
    if (selected) p.set('sel', selected)
    const qs = p.toString()
    return `/practice${qs ? `?${qs}` : ''}`
  })()

  return (
    <div className="practice">
      <header className="practice__top">
        <div>
          <h1>按章節練習</h1>
          <p>答案可按需要顯示；不會限時。顯示答案後可跳至溫習手冊對照章節。</p>
        </div>
      </header>

      <div className="practice__layout">
        <aside className="practice__aside">
          <button
            type="button"
            className={!activeChapter ? 'is-active' : ''}
            onClick={() => selectChapter(null)}
          >
            全部章節
            <span>{data.total}</span>
          </button>
          {groups.map((g) => (
            <button
              key={g.chapter}
              type="button"
              className={activeChapter === g.chapter ? 'is-active' : ''}
              onClick={() => selectChapter(g.chapter || null)}
            >
              <span className="practice__ch-label">
                {g.chapter ? `第 ${g.chapter} 章` : '未分類'}
                <small>{g.title}</small>
              </span>
              <span>{g.questions.length}</span>
            </button>
          ))}
        </aside>

        <section className="practice__main">
          {questions.length === 0 ? (
            <p className="page-status">此章節暫無題目。</p>
          ) : current ? (
            <>
              <div className="practice__nav">
                <button type="button" onClick={() => go(-1)} disabled={cursor === 0}>
                  上一題
                </button>
                <span>
                  {cursor + 1} / {questions.length}
                </span>
                <button
                  type="button"
                  onClick={() => go(1)}
                  disabled={cursor >= questions.length - 1}
                >
                  下一題
                </button>
              </div>

              <QuestionCard
                question={current}
                indexLabel={`第 ${current.number} 題`}
                selected={selected}
                onSelect={(k) => {
                  setSelected(k)
                }}
                showAnswer={revealed}
                manualReturn={{
                  path: returnPath,
                  label: '返回練習題',
                  focusId: current.id,
                }}
              />

              <div className="practice__actions">
                <button
                  type="button"
                  className="btn btn--accent"
                  onClick={() => setRevealed((v) => !v)}
                >
                  {revealed ? '隱藏答案' : '顯示答案與解釋'}
                </button>
              </div>
            </>
          ) : null}
        </section>
      </div>
    </div>
  )
}
