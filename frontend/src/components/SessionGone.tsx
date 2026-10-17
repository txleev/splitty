import { Link } from 'react-router'

export function SessionGone() {
  return (
    <section className="card">
      <h1>This split is gone</h1>
      <p className="muted">
        It does not exist or has expired. Splits expire after 7 days without activity.
      </p>
      <Link to="/" className="btn btn-primary">
        Split a new receipt
      </Link>
    </section>
  )
}
