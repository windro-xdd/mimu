import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.ts'

const AppLayout = () => {
  const { isAuthenticated, user, logout } = useAuth()

  const navLinkClassName = ({ isActive }: { isActive: boolean }) =>
    isActive ? 'nav-link active' : 'nav-link'

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__inner">
          <NavLink to="/" className="brand" aria-label="Application home">
            Acme Portal
          </NavLink>
          <nav aria-label="Primary navigation" className="app-nav">
            <NavLink to="/" end className={navLinkClassName}>
              Home
            </NavLink>
            {isAuthenticated && (
              <>
                <NavLink to="/dashboard" className={navLinkClassName}>
                  Dashboard
                </NavLink>
                <NavLink to="/profile" className={navLinkClassName}>
                  Profile
                </NavLink>
              </>
            )}
          </nav>
          <div className="header-actions">
            {isAuthenticated ? (
              <>
                <span className="user-pill" aria-live="polite">
                  {user?.name}
                </span>
                <button type="button" className="btn btn-secondary" onClick={logout}>
                  Sign out
                </button>
              </>
            ) : (
              <NavLink to="/login" className="btn btn-primary">
                Sign in
              </NavLink>
            )}
          </div>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
      <footer className="app-footer">© {new Date().getFullYear()} Acme Portal</footer>
    </div>
  )
}

export default AppLayout
