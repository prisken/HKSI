import type { MouseEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import type { AnswerKey, Question } from '../types'
import { buildManualHref, EXAM_RESULT_KEY, type ManualReturnState } from '../lib/navigation'
import './QuestionCard.css'

interface Props {
  question: Question
  indexLabel?: string
  selected: AnswerKey | null
  onSelect?: (key: AnswerKey) => void
  showAnswer?: boolean
  disabled?: boolean
  /** Where to return after opening the study-manual link. */
  manualReturn?: ManualReturnState
}

const KEYS: AnswerKey[] = ['A', 'B', 'C', 'D']

export function QuestionCard({
  question,
  indexLabel,
  selected,
  onSelect,
  showAnswer = false,
  disabled = false,
  manualReturn,
}: Props) {
  const navigate = useNavigate()
  const correct = question.answer
  const ref = question.manualRef

  function openManual(e: MouseEvent<HTMLAnchorElement>) {
    if (!ref || !manualReturn) return
    e.preventDefault()
    if (manualReturn.focusId && manualReturn.path.startsWith('/exam')) {
      try {
        const raw = sessionStorage.getItem(EXAM_RESULT_KEY)
        if (raw) {
          const data = JSON.parse(raw) as { focusId?: string }
          data.focusId = manualReturn.focusId
          sessionStorage.setItem(EXAM_RESULT_KEY, JSON.stringify(data))
        }
      } catch {
        /* ignore */
      }
    }
    const href = buildManualHref(ref.path, manualReturn)
    navigate(href)
  }

  return (
    <article className="qcard" id={`q-${question.id}`}>
      <header className="qcard__head">
        <div className="qcard__meta">
          <span className="qcard__badge">
            {indexLabel ?? `第 ${question.number} 題`}
          </span>
          {question.chapter ? (
            <span className="qcard__chapter">
              第 {question.chapter} 章 · {question.chapterTitle || '—'}
            </span>
          ) : null}
          {question.hot ? <span className="qcard__hot">熱門</span> : null}
        </div>
      </header>

      <div className="qcard__stem">
        {question.stem.split('\n').map((line, i) => (
          <p key={i}>{line}</p>
        ))}
      </div>

      <div className="qcard__options" role="radiogroup" aria-label="選項">
        {KEYS.filter((k) => question.options[k] != null && question.options[k] !== '').map((key) => {
          const isSelected = selected === key
          const isCorrect = showAnswer && key === correct
          const isWrong = showAnswer && isSelected && key !== correct
          return (
            <button
              key={key}
              type="button"
              className={[
                'qcard__option',
                isSelected ? 'is-selected' : '',
                isCorrect ? 'is-correct' : '',
                isWrong ? 'is-wrong' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              onClick={() => onSelect?.(key)}
              disabled={disabled || !onSelect}
              aria-checked={isSelected}
              role="radio"
            >
              <span className="qcard__key">{key}</span>
              <span className="qcard__val">{question.options[key]}</span>
            </button>
          )
        })}
      </div>

      {showAnswer ? (
        <div className="qcard__reveal">
          <p className="qcard__answer">
            正確答案：<strong>{correct}</strong>
            {selected && selected !== correct ? (
              <span className="qcard__yours">（你的答案：{selected}）</span>
            ) : null}
          </p>
          {question.explanation ? (
            <div className="qcard__expl">
              <h4>解釋</h4>
              {question.explanation.split('\n').map((line, i) => (
                <p key={i}>{line}</p>
              ))}
            </div>
          ) : null}
          {ref ? (
            <div className="qcard__manual">
              <h4>溫習手冊對照</h4>
              <a
                className="qcard__manual-link"
                href={ref.path}
                onClick={openManual}
              >
                查看：{ref.label}
              </a>
              <p className="qcard__manual-hint">
                開啟後可按「返回」回到目前題目／考試結果。
              </p>
            </div>
          ) : null}
        </div>
      ) : null}
    </article>
  )
}
