import { Link, Route, Routes } from 'react-router'
import { GuestPage } from './pages/GuestPage'
import { HomePage } from './pages/HomePage'
import { HostPage } from './pages/HostPage'

export default function App() {
  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <Link to="/" className="brand">
            <span className="brand-mark" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 3h14v18l-3-2-2 2-2-2-2 2-2-2-3 2z" />
                <path d="M12 8v6" />
                <path d="M9 11h6" />
              </svg>
            </span>
            Splitty
          </Link>
        </div>
      </header>
      <main className="page">
        <Routes>
          <Route index element={<HomePage />} />
          <Route path="s/:sessionId" element={<GuestPage />} />
          <Route path="s/:sessionId/host" element={<HostPage />} />
          <Route
            path="*"
            element={
              <section className="card">
                <h1>Page not found</h1>
                <Link to="/" className="btn btn-primary">
                  Back to start
                </Link>
              </section>
            }
          />
        </Routes>
      </main>
    </>
  )
}
