import { NavLink, useLocation } from 'react-router-dom'
import './AppNav.css'

const LINKS = [
  { to: '/', label: '首頁', match: (path: string) => path === '/' },
  { to: '/manual', label: '溫習手冊', match: (path: string) => path.startsWith('/manual') },
  { to: '/practice', label: '練習', match: (path: string) => path.startsWith('/practice') },
  { to: '/exam', label: '模擬考試', match: (path: string) => path.startsWith('/exam') },
] as const

export function AppNav() {
  const { pathname } = useLocation()

  return (
    <header className="app-nav">
      <div className="app-nav__inner">
        <NavLink to="/" className="app-nav__brand" end>
          <span className="app-nav__brand-mark">HKSI</span>
          <span className="app-nav__brand-text">試卷一</span>
        </NavLink>
        <nav className="app-nav__links" aria-label="主要導覽">
          {LINKS.map((link) => {
            const active = link.match(pathname)
            return (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === '/'}
                className={active ? 'app-nav__link is-active' : 'app-nav__link'}
                aria-current={active ? 'page' : undefined}
              >
                {link.label}
              </NavLink>
            )
          })}
        </nav>
      </div>
    </header>
  )
}
