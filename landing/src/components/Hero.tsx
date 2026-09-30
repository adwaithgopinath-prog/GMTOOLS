import { ArrowDown } from 'lucide-react'
import FeatureStrip from './FeatureStrip'
import HeroActions from './HeroActions'
import IndustrialScene from './IndustrialScene'

export default function Hero() {
  return <section className="hero" id="top"><IndustrialScene /><div className="hero-content"><p className="eyebrow"><span className="eyebrow-rule" />BUILT FOR TOOL MANUFACTURERS &amp; METAL TRADERS.</p><h1>Run your entire<br />business from one<br /><span>connected system.</span></h1><p className="hero-copy">From raw material to finished product. Manage your orders, inventory, production, purchasing, accounting, GST and more — all in one place.</p><HeroActions /></div><div className="hero-bottom"><a className="scroll-cue" href="#product"><span>Built for the way industry works</span><ArrowDown size={14} /></a><FeatureStrip /></div></section>
}
