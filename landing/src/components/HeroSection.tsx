import React, { useEffect, useRef } from 'react'
import HeroCanvas from './HeroCanvas'

// Inline SVG icons to avoid Lucide dependency issues during build
const ArrowRight = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5-5 5M6 12h12" />
  </svg>
)

const PlayCircle = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <circle cx="12" cy="12" r="10" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M10 8l6 4-6 4V8z" />
  </svg>
)

// Animated counter hook
const useCounter = (target: number, duration: number = 1500) => {
  const ref = useRef<HTMLSpanElement>(null)
  const started = useRef(false)

  useEffect(() => {
    const el = ref.current
    if (!el || started.current) return

    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !started.current) {
        started.current = true
        const startTime = performance.now()
        const step = (now: number) => {
          const progress = Math.min((now - startTime) / duration, 1)
          const ease = 1 - Math.pow(1 - progress, 3)
          el.textContent = Math.round(ease * target).toLocaleString('en-IN')
          if (progress < 1) requestAnimationFrame(step)
        }
        requestAnimationFrame(step)
        observer.disconnect()
      }
    }, { threshold: 0.1 })

    observer.observe(el)
    return () => observer.disconnect()
  }, [target, duration])

  return ref
}

// Metric badge component
const MetricBadge: React.FC<{ value: number; suffix: string; label: string; prefix?: string }> = ({
  value, suffix, label, prefix = ''
}) => {
  const ref = useCounter(value)
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="text-2xl font-black text-white stat-number tabular-nums">
        {prefix}<span ref={ref}>0</span>{suffix}
      </div>
      <div className="text-xs text-slate-500 font-medium tracking-wide">{label}</div>
    </div>
  )
}

const HeroSection: React.FC = () => {
  const headlineRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    const el = headlineRef.current
    if (!el) return
    el.style.opacity = '0'
    el.style.transform = 'translateY(20px)'
    requestAnimationFrame(() => {
      el.style.transition = 'opacity 0.7s ease, transform 0.7s ease'
      el.style.opacity = '1'
      el.style.transform = 'translateY(0)'
    })
  }, [])

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden" id="hero">
      {/* Background layers */}
      <div className="absolute inset-0 bg-[#080c14]" />
      <div className="hero-beam absolute inset-0" />
      
      {/* Animated canvas */}
      <div className="canvas-wrapper">
        <HeroCanvas />
      </div>

      {/* Subtle radial highlight at center */}
      <div className="absolute inset-0 pointer-events-none" style={{ background: 'radial-gradient(ellipse 70% 60% at 50% 40%, rgba(30,58,138,0.08), transparent)' }} />

      {/* Content */}
      <div className="relative z-10 max-w-5xl mx-auto px-6 lg:px-8 text-center pt-20">
        
        {/* Eyebrow badge */}
        <div className="inline-flex items-center gap-2.5 bg-blue-500/8 border border-blue-500/15 rounded-full px-4 py-2 mb-10 animate-fade-up" style={{ animationDelay: '0.1s' }}>
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
          <span className="text-xs font-semibold text-blue-300 tracking-wide">Built for Indian Steel & Cutting-Tool Industry</span>
          <svg className="w-3.5 h-3.5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5-5 5M6 12h12" />
          </svg>
        </div>

        {/* Main headline */}
        <h1
          ref={headlineRef}
          className="text-5xl sm:text-6xl lg:text-[80px] font-black text-white leading-[1.05] tracking-tight mb-6"
        >
          Command Your
          <br />
          <span className="gradient-text-blue">Steel Operations</span>
          <br />
          <span className="text-slate-400">with Precision</span>
        </h1>

        {/* Subtitle */}
        <p
          className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed animate-fade-up font-light"
          style={{ animationDelay: '0.3s' }}
        >
          GMTOOLS is the all-in-one ERP platform built exclusively for{' '}
          <span className="text-slate-200 font-medium">cutting-tool manufacturers</span> and{' '}
          <span className="text-slate-200 font-medium">steel/metal trading businesses</span> — 
          from floor orders to financial command.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16 animate-fade-up" style={{ animationDelay: '0.4s' }}>
          <a href="http://localhost:5000/login" className="btn-primary text-base px-8 py-3.5 shadow-xl shadow-blue-500/20">
            Launch GMTOOLS
            <ArrowRight />
          </a>
          <button className="btn-secondary text-base px-8 py-3.5">
            <PlayCircle />
            Watch Demo
          </button>
        </div>

        {/* Stats bar */}
        <div
          className="inline-flex items-center gap-8 sm:gap-12 bg-white/[0.03] border border-white/[0.07] rounded-2xl px-8 py-5 animate-fade-up"
          style={{ animationDelay: '0.55s' }}
        >
          <MetricBadge value={2500} suffix="+" label="Orders Managed" />
          <div className="w-px h-8 bg-white/10" />
          <MetricBadge value={98} suffix="%" label="Uptime SLA" />
          <div className="w-px h-8 bg-white/10" />
          <MetricBadge value={50} suffix="+" label="Product SKUs" />
          <div className="hidden sm:block w-px h-8 bg-white/10" />
          <div className="hidden sm:flex flex-col items-center gap-1">
            <div className="text-2xl font-black text-white">₹ Cr+</div>
            <div className="text-xs text-slate-500 font-medium tracking-wide">Revenue Tracked</div>
          </div>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 animate-bounce">
        <span className="text-xs text-slate-600 font-medium tracking-wider uppercase">Scroll</span>
        <div className="w-px h-6 bg-gradient-to-b from-slate-600 to-transparent" />
      </div>

      {/* Bottom edge gradient */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#080c14] to-transparent pointer-events-none" />
    </section>
  )
}

export default HeroSection
