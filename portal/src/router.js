import { useEffect, useState } from 'react'

// Tiny hash router: "#/facilitator?s=round" -> { page: 'facilitator', section: 'round' }
function parse() {
  const raw = window.location.hash.replace(/^#\/?/, '')
  const [path, query = ''] = raw.split('?')
  const section = new URLSearchParams(query).get('s')
  return { page: path || 'home', section }
}

export function useRoute() {
  const [route, setRoute] = useState(parse)
  useEffect(() => {
    const on = () => setRoute(parse())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return route
}

export const href = (page, section) => `#/${page === 'home' ? '' : page}${section ? `?s=${section}` : ''}`
