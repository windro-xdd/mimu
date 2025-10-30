import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { AUTH_UNAUTHORIZED_EVENT } from '../lib/apiClient.ts'
import { AuthContext, type AuthUser } from './auth-context.ts'

const AUTH_STORAGE_KEY = 'app.auth.session'

type AuthProviderProps = {
  children: ReactNode
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (typeof window === 'undefined') {
      setIsLoading(false)
      return
    }

    try {
      const stored = window.localStorage.getItem(AUTH_STORAGE_KEY)
      if (stored) {
        const parsed: AuthUser = JSON.parse(stored)
        setUser(parsed)
      }
    } catch (error) {
      console.warn('Unable to restore auth session', error)
      window.localStorage.removeItem(AUTH_STORAGE_KEY)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const login = useCallback((userData: AuthUser) => {
    setUser(userData)

    if (typeof window !== 'undefined') {
      window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(userData))
    }
  }, [])

  const logout = useCallback(() => {
    setUser(null)

    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(AUTH_STORAGE_KEY)
    }
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined
    }

    const handleUnauthorized = () => {
      logout()
    }

    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized)
    return () => window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized)
  }, [logout])

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: user != null,
      isLoading,
      login,
      logout,
    }),
    [user, isLoading, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
