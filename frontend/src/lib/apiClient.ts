import axios, { AxiosHeaders } from 'axios'

export const AUTH_UNAUTHORIZED_EVENT = 'auth:unauthorized' as const
const CSRF_COOKIE_NAME = 'csrfToken'
const CSRF_HEADER_NAME = 'X-CSRF-Token'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  withCredentials: true,
})

const getCookie = (name: string) => {
  if (typeof document === 'undefined') {
    return null
  }

  const cookieString = document.cookie
  if (!cookieString) {
    return null
  }

  const cookies = cookieString.split('; ')
  for (const cookie of cookies) {
    const [cookieName, ...cookieValue] = cookie.split('=')
    if (decodeURIComponent(cookieName) === name) {
      return decodeURIComponent(cookieValue.join('='))
    }
  }

  return null
}

apiClient.interceptors.request.use((config) => {
  const csrfToken = getCookie(CSRF_COOKIE_NAME)

  if (csrfToken) {
    const headers = config.headers instanceof AxiosHeaders ? config.headers : AxiosHeaders.from(config.headers ?? {})
    headers.set(CSRF_HEADER_NAME, csrfToken)
    config.headers = headers
  }

  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT))
    }

    if (error.response) {
      console.error('API error response', error.response)
    } else if (error.request) {
      console.error('API request error', error.request)
    } else {
      console.error('API error', error.message)
    }

    return Promise.reject(error)
  },
)

export default apiClient
