import type { AnswerKey, Question } from '../types'
import './QuestionCard.css'

interface Props {
  question: Question
  indexLabel?: string
  selected: AnswerKey | null
  onSelect?: (key: AnswerKey) => void
  showAnswer?: boolean
  disabled?: boolean
}

const KEYS: AnswerKey[] = ['A', 'B', 'C', 'D']

export function QuestionCard({
  question,
  indexLabel,
  selected,
  onSelect,
  showAnswer = false,
  disabled = false,
}: Props) {
  const correct = question.answer

  return (
    <article className="qcard">
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
        </div>
      ) : null}
    </article>
  )
}
