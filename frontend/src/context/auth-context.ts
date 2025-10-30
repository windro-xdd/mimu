import { createContext } from 'react'

export type AuthUser = {
  email: string
  name: string
}

export type AuthContextValue = {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (userData: AuthUser) => void
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)
