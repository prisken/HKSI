import { Link } from 'react-router-dom'
import { EXAM_CONFIG, CHAPTER_TITLES } from '../lib/exam'
import { useQuestionBank } from '../hooks/useQuestionBank'
import './HomePage.css'

export function HomePage() {
  const { data, loading, error } = useQuestionBank()
  const total = data?.total ?? 0
  const chapterCount = data
    ? new Set(data.questions.map((q) => q.chapter).filter(Boolean)).size
    : 0

  return (
    <div className="home">
      <section className="home__hero">
        <p className="home__brand">HKSI 試卷一</p>
        <h1>基本證券及期貨規例<br />練習與模擬考試</h1>
        <p className="home__lead">
          以練習題庫按章節溫習，或以溫習手冊考試規格抽題進行 60 題限時模擬試。
        </p>
        <div className="home__stats" aria-live="polite">
          {loading ? <span>正在載入題庫…</span> : null}
          {error ? <span className="home__err">{error}</span> : null}
          {data ? (
            <>
              <span>{total} 題已匯入</span>
              <span>·</span>
              <span>{chapterCount} 個章節</span>
            </>
          ) : null}
        </div>
      </section>

      <section className="home__modes">
        <Link to="/practice" className="mode mode--practice">
          <span className="mode__kicker">模式一</span>
          <h2>按章節練習</h2>
          <p>瀏覽全部練習題，按章節分類。可隨時顯示答案與解釋。</p>
        </Link>
        <Link to="/exam" className="mode mode--exam">
          <span className="mode__kicker">模式二</span>
          <h2>模擬考試</h2>
          <p>
            {EXAM_CONFIG.totalQuestions} 題 · {EXAM_CONFIG.durationMinutes} 分鐘 · 合格{' '}
            {EXAM_CONFIG.passPercent}%
            。按章節比重隨機抽題，提交後才顯示成績與解釋。
          </p>
        </Link>
      </section>

      <section className="home__weights">
        <h3>模擬考試章節題數分配</h3>
        <p className="home__weights-note">
          溫習手冊訂明試卷一為 60 條多項選擇題、90 分鐘、合格分數 70%。下列各章題數按常見試卷一比重估算。
        </p>
        <ol className="home__weight-list">
          {Object.keys(EXAM_CONFIG.chapterCounts).map(Number).map((ch) => (
            <li key={ch}>
              <span>
                第 {ch} 章 {CHAPTER_TITLES[ch]}
              </span>
              <strong>{EXAM_CONFIG.chapterCounts[ch]} 題</strong>
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}
