import { useEffect, useRef } from 'react'

export default function IndustrialScene() {
  const sceneRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const scene = sceneRef.current
    if (!scene || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    let frame = 0
    let targetX = 0
    let targetY = 0
    let currentX = 0
    let currentY = 0
    const move = (event: PointerEvent) => {
      targetX = (event.clientX / window.innerWidth - 0.5) * 5
      targetY = (event.clientY / window.innerHeight - 0.5) * 3
    }
    const render = () => {
      currentX += (targetX - currentX) * 0.025
      currentY += (targetY - currentY) * 0.025
      scene.style.setProperty('--drift-x', `${currentX}px`)
      scene.style.setProperty('--drift-y', `${currentY}px`)
      frame = requestAnimationFrame(render)
    }
    window.addEventListener('pointermove', move, { passive: true })
    frame = requestAnimationFrame(render)
    return () => { window.removeEventListener('pointermove', move); cancelAnimationFrame(frame) }
  }, [])
  return <div ref={sceneRef} className="industrial-scene" aria-hidden="true"><div className="scene-image" /><div className="scene-vignette" /><div className="scene-grain" /></div>
}
