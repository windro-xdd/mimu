class AuthContext {
  constructor(initialUser = null) {
    this.state = {
      user: initialUser,
    };
    this.subscribers = new Set();
  }

  getUser() {
    return this.state.user;
  }

  setUser(user) {
    this.state.user = user;
    this.notify();
  }

  hasRole(role) {
    const { user } = this.state;
    if (!user || !user.role) return false;

    const normalisedRole = String(role).toLowerCase();
    if (Array.isArray(user.role)) {
      return user.role.map((item) => String(item).toLowerCase()).includes(normalisedRole);
    }

    return String(user.role).toLowerCase() === normalisedRole;
  }

  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  notify() {
    this.subscribers.forEach((callback) => {
      try {
        callback(this.state.user);
      } catch (error) {
        console.error("AuthContext subscriber error", error);
      }
    });
  }
}

function deriveBootstrapUser() {
  if (window.APP_BOOTSTRAP && window.APP_BOOTSTRAP.currentUser) {
    return window.APP_BOOTSTRAP.currentUser;
  }

  const role = document.body?.dataset?.userRole;
  if (role) {
    return {
      id: "anonymous",
      name: "Guest",
      role,
    };
  }

  return null;
}

export const authContext = new AuthContext(deriveBootstrapUser());

export function requireRole(role) {
  return authContext.hasRole(role);
}

export function onAuthChange(callback) {
  return authContext.subscribe(callback);
}

export function setCurrentUser(user) {
  authContext.setUser(user);
}
