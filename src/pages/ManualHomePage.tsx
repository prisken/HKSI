import { Link } from 'react-router-dom'
import { useManualMeta } from '../hooks/useManual'
import './ManualPage.css'

export function ManualHomePage() {
  const { meta, loading, error } = useManualMeta()

  if (loading) return <p className="page-status">載入溫習手冊…</p>
  if (error) return <p className="page-status page-status--err">{error}</p>
  if (!meta) return null

  return (
    <div className="manual manual--home">
      <header className="manual__top">
        <div className="manual__version-badge" title={`版本識別：${meta.versionId}`}>
          <span className="manual__ver-label">溫習手冊 {meta.versionFull}</span>
          <span className="manual__ver-date">內容更新至 {meta.updatedThroughLabel}</span>
        </div>
      </header>

      <section className="manual__intro">
        <p className="manual__kicker">{meta.edition}</p>
        <h1>{meta.paper}</h1>
        <p className="manual__lead">
          按章節與小節閱讀。可從左側／下方目錄跳至指定章節；進入章節後可再跳到小節。
        </p>
        <dl className="manual__meta">
          <div>
            <dt>版本</dt>
            <dd>
              {meta.edition} · {meta.versionFull}
            </dd>
          </div>
          <div>
            <dt>初版</dt>
            <dd>{meta.firstPublishedLabel}</dd>
          </div>
          <div>
            <dt>目前更新至</dt>
            <dd>
              <strong>{meta.updatedThroughLabel}</strong>
              <span className="manual__meta-sub">（{meta.updatedThrough}）</span>
            </dd>
          </div>
          <div>
            <dt>出版</dt>
            <dd>{meta.publisher}</dd>
          </div>
        </dl>
        {meta.notes?.length ? (
          <ul className="manual__notes">
            {meta.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="manual__chapters">
        <h2>章節目錄</h2>
        <ol className="manual__chapter-list">
          {meta.chapters.map((ch) => (
            <li key={ch.id}>
              <Link to={`/manual/${ch.number}`}>
                <span className="manual__ch-num">第 {ch.number} 章</span>
                <span className="manual__ch-title">{ch.title}</span>
                <span className="manual__ch-count">{ch.sectionCount} 節</span>
              </Link>
            </li>
          ))}
        </ol>
      </section>

      {meta.extras?.length ? (
        <section className="manual__extras">
          <h2>附錄／更新說明</h2>
          <ul>
            {meta.extras.map((ex) => (
              <li key={ex.id}>
                <Link to={`/manual/extra/${ex.id}`}>{ex.title}</Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  )
}
