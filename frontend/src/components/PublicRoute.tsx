import { Navigate, Outlet, useLocation } from 'react-router-dom'
import LoadingScreen from './LoadingScreen.tsx'
import { useAuth } from '../hooks/useAuth.ts'

const PublicRoute = () => {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <LoadingScreen />
  }

  if (isAuthenticated) {
    const from = (location.state as { from?: string } | undefined)?.from
    return <Navigate to={from ?? '/dashboard'} replace />
  }

  return <Outlet />
}

export default PublicRoute
