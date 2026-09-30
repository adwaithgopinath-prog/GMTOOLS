import { type LucideIcon } from 'lucide-react'

export default function FeatureItem({ icon: Icon, label }: { icon: LucideIcon; label: string }) {
  return <span className="feature-item"><Icon size={17} strokeWidth={1.55} /><span>{label}</span></span>
}
