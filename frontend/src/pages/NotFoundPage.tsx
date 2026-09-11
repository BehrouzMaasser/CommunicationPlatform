import { Link } from 'react-router-dom'

function NotFoundPage() {
  return (
    <section className="text-center py-5">
      <p className="display-1 fw-semibold mb-2">404</p>
      <h1 className="h3 mb-3">Page not found</h1>
      <p className="text-secondary mb-4">
        React Router could not match this URL.
      </p>
      <Link className="btn btn-primary" to="/">
        Back home
      </Link>
    </section>
  )
}

export default NotFoundPage
