import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
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

  const [cursor, setCursor] = useState(0)
  const [selected, setSelected] = useState<AnswerKey | null>(null)
  const [revealed, setRevealed] = useState(false)

  const groups = useMemo(() => (data ? groupByChapter(data.questions) : []), [data])
  const questions = useMemo(() => {
    if (!data) return []
    if (activeChapter == null) return data.questions
    return data.questions.filter((q) => q.chapter === activeChapter)
  }, [data, activeChapter])

  const current = questions[cursor] ?? null

  function selectChapter(ch: number | null) {
    setCursor(0)
    setSelected(null)
    setRevealed(false)
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

  return (
    <div className="practice">
      <header className="practice__top">
        <Link to="/" className="back">
          ← 返回
        </Link>
        <div>
          <h1>按章節練習</h1>
          <p>答案可按需要顯示；不會限時。</p>
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
