/** Render a user-facing request error without exposing provider details. */
function ErrorMessage({ message }) {
  if (!message) {
    return null
  }

  return (
    <div className='error-message' role='alert'>
      <span className='error-message__mark' aria-hidden='true'>!</span>
      <span>{message}</span>
    </div>
  )
}

export default ErrorMessage
