import { ArrowRight, Play } from 'lucide-react'

export default function HeroActions() {
  return <div className="hero-actions"><a className="primary-action" href="/register">Get Started <ArrowRight size={16} /></a><a className="secondary-action" href="#product"><span className="play-icon"><Play size={11} fill="currentColor" /></span>See How It Works</a></div>
}
