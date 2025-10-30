import { useAuth } from '../hooks/useAuth.ts'

const ProfilePage = () => {
  const { user } = useAuth()

  return (
    <section className="page">
      <header className="page-header">
        <h1>Profile</h1>
        <p>Manage your account details and personal preferences.</p>
      </header>
      <div className="page-content">
        <div className="card">
          <h2>Account information</h2>
          {user ? (
            <dl className="definition-list">
              <div>
                <dt>Name</dt>
                <dd>{user.name}</dd>
              </div>
              <div>
                <dt>Email</dt>
                <dd>{user.email}</dd>
              </div>
            </dl>
          ) : (
            <p>Your profile information will appear here once you are signed in.</p>
          )}
        </div>
      </div>
    </section>
  )
}

export default ProfilePage
