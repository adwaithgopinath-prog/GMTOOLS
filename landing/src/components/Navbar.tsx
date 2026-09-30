import { ArrowRight, Menu, X } from 'lucide-react'
import { useState } from 'react'

const links = [['Operations', '#operations']]

export default function Navbar() {
  const [open, setOpen] = useState(false)
  return <header className="site-header"><nav className="nav-shell" aria-label="Main navigation">
    <a href="#top" className="wordmark" aria-label="GMTOOLS home"><span className="brand-mark">GM</span><span>GMTOOLS</span></a>
    <div className="nav-links">{links.map(([label, href]) => <a key={label} href={href}>{label}</a>)}</div>
    <div className="nav-actions"><a className="nav-cta" href="/login">Open workspace <ArrowRight size={15} /></a></div>
    <button className="menu-toggle" aria-label={open ? 'Close navigation menu' : 'Open navigation menu'} aria-expanded={open} onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button>
  </nav>{open && <div className="mobile-nav">{links.map(([label, href]) => <a key={label} href={href} onClick={() => setOpen(false)}>{label}</a>)}<a className="mobile-cta" href="/login">Open workspace <ArrowRight size={15} /></a></div>}</header>
}
