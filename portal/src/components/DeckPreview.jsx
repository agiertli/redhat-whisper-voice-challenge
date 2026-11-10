import { useEffect, useRef, useState } from 'react'

// Renders the stage deck at its native size and scales it to fit, so nothing is cropped.
const W = 1440, H = 900

export default function DeckPreview({ src }) {
  const box = useRef(null)
  const [k, setK] = useState(0.5)
  useEffect(() => {
    const ro = new ResizeObserver(([e]) => setK(e.contentRect.width / W))
    ro.observe(box.current)
    return () => ro.disconnect()
  }, [])
  return (
    <div ref={box} style={{ position: 'relative', height: H * k, overflow: 'hidden', background: '#151515' }}>
      <iframe src={src} title="Example award ceremony deck" loading="lazy"
        style={{ width: W, height: H, border: 0, transform: `scale(${k})`, transformOrigin: '0 0', position: 'absolute', left: 0, top: 0 }} />
    </div>
  )
}
