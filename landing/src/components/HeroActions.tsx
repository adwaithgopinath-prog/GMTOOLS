import { ArrowRight, MoveDown } from 'lucide-react'

export default function HeroActions() {
  return <div className="hero-actions"><a className="primary-action" href="/login">Sign in to GMTOOLS <ArrowRight size={16} /></a><a className="secondary-action" href="#operations"><span className="play-icon"><MoveDown size={13} /></span>Explore modules</a></div>
}
