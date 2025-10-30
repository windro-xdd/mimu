const LoadingScreen = () => {
  return (
    <div className="loading-screen" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <p>Loading...</p>
    </div>
  )
}

export default LoadingScreen
