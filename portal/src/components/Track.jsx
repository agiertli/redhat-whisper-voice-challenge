import { useEffect, useState } from 'react'
import { href } from '../router.js'

// Two-column track page: sticky contents on the left, chapters on the right.
export function Track({ page, sections, section, children, extra }) {
  const [active, setActive] = useState(sections[0].id)

  useEffect(() => {
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && setActive(e.target.id)),
      { rootMargin: '-30% 0px -60% 0px' },
    )
    sections.forEach((s) => { const el = document.getElementById(s.id); if (el) io.observe(el) })
    return () => io.disconnect()
  }, [sections])

  useEffect(() => {
    if (section) document.getElementById(section)?.scrollIntoView()
    else window.scrollTo(0, 0)
  }, [section])

  const go = (e, id) => {
    e.preventDefault()
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className="wrap track">
      <nav className="toc" aria-label="On this page">
        <ol>
          {sections.map((s) => (
            <li key={s.id}><a href={href(page, s.id)} onClick={(e) => go(e, s.id)} className={active === s.id ? 'on' : ''}>{s.title}</a></li>
          ))}
        </ol>
        {extra}
      </nav>
      <div>{children}</div>
    </div>
  )
}

export const Chapter = ({ id, title, lede, children }) => (
  <section className="chapter" id={id} aria-labelledby={`${id}-h`}>
    <h2 id={`${id}-h`}>{title}</h2>
    {lede && <p className="lede">{lede}</p>}
    {children}
  </section>
)
