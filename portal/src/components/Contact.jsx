// Address assembled at runtime so it doesn't sit in the HTML for scrapers.
const addr = () => ['agiertli', 'redhat.com'].join('@')

export function Mail({ children }) {
  return <a href="#" onClick={(e) => { e.preventDefault(); window.location.href = `mailto:${addr()}?subject=Whisper%20Voice%20Challenge` }}>{children}</a>
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
