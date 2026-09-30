import { ArrowUpRight, Menu, Search, X } from 'lucide-react'
import { useState } from 'react'

const links = [
  ['Product', '#product'], ['Solutions', '#solutions'], ['Industries', '#industries'],
  ['Pricing', '#pricing'], ['Resources', '#resources'], ['Contact', 'mailto:hello@gmtools.in'],
]

export default function Navbar() {
  const [open, setOpen] = useState(false)
  return <header className="site-header"><nav className="nav-shell" aria-label="Main navigation">
    <a href="#top" className="wordmark" aria-label="GMTOOLS home"><span className="brand-mark">GM</span><span>GMTOOLS</span></a>
    <div className="nav-links">{links.map(([label, href]) => <a key={label} href={href}>{label}</a>)}</div>
    <div className="nav-actions"><button className="search-button" aria-label="Search"><Search size={16} strokeWidth={1.7} /></button><a className="sign-in" href="/login">Sign in</a><a className="nav-cta" href="/register">Get Started <ArrowUpRight size={15} /></a></div>
    <button className="menu-toggle" aria-label={open ? 'Close navigation menu' : 'Open navigation menu'} aria-expanded={open} onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button>
  </nav>{open && <div className="mobile-nav">{links.map(([label, href]) => <a key={label} href={href} onClick={() => setOpen(false)}>{label}</a>)}<a href="/login">Sign in</a><a className="mobile-cta" href="/register">Get Started <ArrowUpRight size={15} /></a></div>}</header>
}
