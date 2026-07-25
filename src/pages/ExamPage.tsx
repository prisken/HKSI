import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { QuestionCard } from '../components/QuestionCard'
import { useQuestionBank } from '../hooks/useQuestionBank'
import {
  CHAPTER_TITLES,
  EXAM_CONFIG,
  buildExamPaper,
  formatTime,
  scoreExam,
} from '../lib/exam'
import type { AnswerKey, ExamQuestion } from '../types'
import './ExamPage.css'

type Phase = 'intro' | 'running' | 'result'

export function ExamPage() {
  const { data, loading, error } = useQuestionBank()
  const [phase, setPhase] = useState<Phase>('intro')
  const [paper, setPaper] = useState<ExamQuestion[]>([])
  const [answers, setAnswers] = useState<Record<string, AnswerKey | null>>({})
  const [cursor, setCursor] = useState(0)
  const [remaining, setRemaining] = useState(EXAM_CONFIG.durationMinutes * 60)
  const [elapsed, setElapsed] = useState(0)

  const answeredCount = useMemo(
    () => Object.values(answers).filter(Boolean).length,
    [answers],
  )

  useEffect(() => {
    if (phase !== 'running') return
    const id = window.setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          window.clearInterval(id)
          setPhase('result')
          return 0
        }
        return r - 1
      })
      setElapsed((e) => e + 1)
    }, 1000)
    return () => window.clearInterval(id)
  }, [phase])

  function startExam() {
    if (!data) return
    const next = buildExamPaper(data.questions, EXAM_CONFIG)
    setPaper(next)
    setAnswers(Object.fromEntries(next.map((q) => [q.id, null])))
    setCursor(0)
    setRemaining(EXAM_CONFIG.durationMinutes * 60)
    setElapsed(0)
    setPhase('running')
  }

  function submit() {
    const unanswered = paper.length - answeredCount
    if (unanswered > 0) {
      const ok = window.confirm(`尚有 ${unanswered} 題未作答，確定提交？`)
      if (!ok) return
    }
    setPhase('result')
  }

  if (loading) return <p className="page-status">載入題庫中…</p>
  if (error) return <p className="page-status page-status--err">{error}</p>
  if (!data) return null

  if (phase === 'intro') {
    const available = Object.keys(EXAM_CONFIG.chapterCounts).map(Number).map((ch) => {
      const need = EXAM_CONFIG.chapterCounts[ch]
      const have = data.questions.filter((q) => q.chapter === ch).length
      return { ch, need, have }
    })

    return (
      <div className="exam exam--intro">
        <h1>模擬考試</h1>
        <p className="exam__lead">
          系統會按溫習手冊考試規格（{EXAM_CONFIG.totalQuestions} 題／
          {EXAM_CONFIG.durationMinutes} 分鐘／合格 {EXAM_CONFIG.passPercent}%）
          ，並依各章比重從練習題庫隨機抽題。提交全部答案後才會顯示成績、正確答案與解釋。
        </p>

        <ul className="exam__rules">
          <li>共 {EXAM_CONFIG.totalQuestions} 條多項選擇題</li>
          <li>限時 {EXAM_CONFIG.durationMinutes} 分鐘；時間到自動交卷</li>
          <li>合格分數 {EXAM_CONFIG.passPercent}%（即至少 {Math.ceil(EXAM_CONFIG.totalQuestions * EXAM_CONFIG.passPercent / 100)} 題正解）</li>
          <li>答錯不扣分</li>
        </ul>

        <div className="exam__coverage">
          <h3>題庫覆蓋（抽題來源）</h3>
          <ul>
            {available.map((row) => (
              <li key={row.ch} className={row.have < row.need ? 'is-short' : ''}>
                <span>
                  第 {row.ch} 章 {CHAPTER_TITLES[row.ch]}
                </span>
                <span>
                  需要 {row.need} · 庫存 {row.have}
                </span>
              </li>
            ))}
          </ul>
          <p className="exam__coverage-note">
            若某章題目不足，系統會以其他章節題目補足至 {EXAM_CONFIG.totalQuestions} 題。
          </p>
        </div>

        <button type="button" className="btn btn--accent btn--lg" onClick={startExam}>
          開始模擬考試
        </button>
      </div>
    )
  }

  const current = paper[cursor]
  const result = phase === 'result' ? scoreExam(paper, answers) : null

  if (phase === 'result' && result) {
    return (
      <div className="exam exam--result">
        <header className={`exam__score ${result.passed ? 'is-pass' : 'is-fail'}`}>
          <p className="exam__score-kicker">{result.passed ? '合格' : '未合格'}</p>
          <h1>
            {result.score} / {paper.length}
          </h1>
          <p>
            得分 {result.percent}% · 用時 {formatTime(elapsed)}
          </p>
        </header>

        <div className="exam__result-actions">
          <button type="button" className="btn btn--accent" onClick={startExam}>
            再考一次
          </button>
          <Link to="/practice" className="btn">
            返回章節練習
          </Link>
        </div>

        <section className="exam__review">
          <h2>逐題檢討</h2>
          {paper.map((q, i) => (
            <QuestionCard
              key={q.id}
              question={q}
              indexLabel={`第 ${i + 1} 題（題庫 #${q.number}）`}
              selected={answers[q.id]}
              showAnswer
              disabled
            />
          ))}
        </section>
      </div>
    )
  }

  return (
    <div className="exam exam--run">
      <header className="exam__bar">
        <div>
          <strong>
            第 {cursor + 1} / {paper.length} 題
          </strong>
          <span>
            已答 {answeredCount}/{paper.length}
          </span>
        </div>
        <div className={`exam__timer ${remaining <= 300 ? 'is-low' : ''}`}>
          {formatTime(remaining)}
        </div>
        <button type="button" className="btn btn--accent" onClick={submit}>
          交卷
        </button>
      </header>

      <div className="exam__grid">
        <div className="exam__palette" aria-label="題號">
          {paper.map((q, i) => (
            <button
              key={q.id}
              type="button"
              className={[
                answers[q.id] ? 'is-answered' : '',
                i === cursor ? 'is-current' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              onClick={() => setCursor(i)}
            >
              {i + 1}
            </button>
          ))}
        </div>

        <div className="exam__body">
          {current ? (
            <QuestionCard
              question={current}
              indexLabel={`第 ${cursor + 1} 題`}
              selected={answers[current.id]}
              onSelect={(k) => setAnswers((prev) => ({ ...prev, [current.id]: k }))}
              showAnswer={false}
            />
          ) : null}

          <div className="exam__nav">
            <button type="button" className="btn" disabled={cursor === 0} onClick={() => setCursor((c) => c - 1)}>
              上一題
            </button>
            <button
              type="button"
              className="btn"
              disabled={cursor >= paper.length - 1}
              onClick={() => setCursor((c) => c + 1)}
            >
              下一題
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
