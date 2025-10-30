import type { FormEvent } from 'react'
import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.ts'

const LoginPage = () => {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [name, setName] = useState('Jane Doe')
  const [email, setEmail] = useState('jane@example.com')
  const [error, setError] = useState('')

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!email.trim()) {
      setError('Email is required to sign in.')
      return
    }

    login({ name: name.trim() || 'Jane Doe', email: email.trim() })

    const redirectTo = (location.state as { from?: string } | undefined)?.from ?? '/dashboard'
    navigate(redirectTo, { replace: true })
  }

  return (
    <section className="page">
      <header className="page-header">
        <h1>Sign in</h1>
        <p>Authenticate to access the private areas of this application.</p>
      </header>
      <div className="page-content">
        <form className="form-card" onSubmit={handleSubmit} noValidate>
          <div className="form-field">
            <label htmlFor="name">Name</label>
            <input
              id="name"
              name="name"
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className="form-field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value)
                if (error) {
                  setError('')
                }
              }}
              required
            />
          </div>
          {error && <p className="form-error">{error}</p>}
          <button type="submit" className="btn btn-primary">
            Continue
          </button>
        </form>
      </div>
    </section>
  )
}

export default LoginPage
