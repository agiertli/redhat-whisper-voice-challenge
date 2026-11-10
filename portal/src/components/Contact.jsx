import { useState } from 'react'

// Address assembled at runtime so it doesn't sit in the HTML for scrapers.
const addr = () => ['agiertli', 'redhat.com'].join('@')

// mailto: silently does nothing when no mail app is configured (webmail users),
// so the click also reveals the address and copies it.
export function Mail({ children }) {
  const [shown, setShown] = useState(false)
  const [copied, setCopied] = useState(false)
  const reveal = (e) => {
    e.preventDefault()
    setShown(true)
    navigator.clipboard?.writeText(addr()).then(() => setCopied(true), () => {})
    window.location.href = `mailto:${addr()}?subject=Whisper%20Voice%20Challenge`
  }
  if (shown) {
    return (
      <span>
        <a href={`mailto:${addr()}?subject=Whisper%20Voice%20Challenge`}>{addr()}</a>
        {copied && <span className="copied" role="status"> (copied)</span>}
      </span>
    )
  }
  return <a href="#" onClick={reveal}>{children}</a>
}

export default function Contact() {
  return (
    <aside className="contact">
      <h3>Want to talk to the person who built it?</h3>
      <p>
        Whisper Voice Challenge was created by Anton Giertli, Senior Solution Architect at Red Hat.
        Planning an event, stuck on something, or have an idea? <Mail>Drop Anton a message</Mail>.
      </p>
    </aside>
  )
}
