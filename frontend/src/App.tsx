import { Link, Route, Routes } from 'react-router'
import { GuestPage } from './pages/GuestPage'
import { HomePage } from './pages/HomePage'
import { HostPage } from './pages/HostPage'

export default function App() {
  return (
    <>
      <header className="topbar">
        <Link to="/" className="brand">
          Splitty
        </Link>
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
