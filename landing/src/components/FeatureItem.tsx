import { ArrowUpRight, type LucideIcon } from 'lucide-react'

export default function FeatureItem({ icon: Icon, label }: { icon: LucideIcon; label: string }) {
  return <a className="feature-item" href="#product"><Icon size={17} strokeWidth={1.55} /><span>{label}</span><ArrowUpRight className="feature-arrow" size={13} /></a>
}
