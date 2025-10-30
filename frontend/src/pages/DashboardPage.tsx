import { useAuth } from '../hooks/useAuth.ts'

const DashboardPage = () => {
  const { user } = useAuth()

  return (
    <section className="page">
      <header className="page-header">
        <h1>Dashboard</h1>
        <p>Overview of your latest activity and quick entry points to core tools.</p>
      </header>
      <div className="page-content">
        <div className="card-grid">
          <article className="card">
            <h2>Hello, {user?.name ?? 'there'} 👋</h2>
            <p>
              This is a placeholder dashboard view. Replace it with charts, tables, or workflow widgets as your
              application evolves.
            </p>
          </article>
          <article className="card">
            <h3>Next steps</h3>
            <ul>
              <li>Connect to your real API</li>
              <li>Populate this page with authenticated data</li>
              <li>Refine the layout to match your brand</li>
            </ul>
          </article>
        </div>
      </div>
    </section>
  )
}

export default DashboardPage
