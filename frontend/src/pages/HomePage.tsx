import { Link } from 'react-router-dom'
import LoadingScreen from '../components/LoadingScreen.tsx'
import { useAuth } from '../hooks/useAuth.ts'

const HomePage = () => {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <LoadingScreen />
  }

  return (
    <section className="page">
      <header className="page-header">
        <h1>Welcome to the Acme Portal</h1>
        <p>Your central hub for managing projects, tracking progress, and collaborating with your team.</p>
      </header>
      <div className="page-content">
        <p>
          {isAuthenticated
            ? 'Head to your dashboard to pick up where you left off.'
            : 'Sign in to access your personalised workspace and keep things moving.'}
        </p>
        <div className="cta-group">
          <Link to={isAuthenticated ? '/dashboard' : '/login'} className="btn btn-primary">
            {isAuthenticated ? 'Go to dashboard' : 'Sign in'}
          </Link>
          <Link to="/profile" className="btn btn-ghost">
            View profile
          </Link>
        </div>
      </div>
    </section>
  )
}

export default HomePage
