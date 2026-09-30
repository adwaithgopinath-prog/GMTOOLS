import { Boxes, ClipboardList, Factory, FileCheck2, PackageSearch, Truck, WalletCards } from 'lucide-react'
import FeatureItem from './FeatureItem'

const features = [
  [ClipboardList, 'Sales & CRM'], [PackageSearch, 'Inventory'], [Factory, 'Production'],
  [Boxes, 'Purchasing'], [WalletCards, 'Accounting'], [FileCheck2, 'GST & Compliance'], [Truck, 'Dispatch & Logistics'],
] as const

export default function FeatureStrip() {
  return <nav id="operations" className="feature-strip" aria-label="GMTOOLS capabilities">{features.map(([icon, label]) => <FeatureItem key={label} icon={icon} label={label} />)}</nav>
}
