import { Link } from 'react-router-dom'

const NotFoundPage = () => {
  return (
    <section className="page">
      <header className="page-header">
        <h1>Page not found</h1>
        <p>The page you were looking for could not be located.</p>
      </header>
      <div className="page-content">
        <p>Check the address and try again, or head back to the dashboard.</p>
        <Link to="/" className="btn btn-primary">
          Return home
        </Link>
      </div>
    </section>
  )
}

export default NotFoundPage
