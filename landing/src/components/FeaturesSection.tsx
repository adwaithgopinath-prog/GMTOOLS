import React from 'react'

interface Feature {
  icon: React.ReactNode
  title: string
  description: string
  tag: string
  tagColor: string
}

const BarChart2 = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>
)
const Package = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
  </svg>
)
const FileText = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
)
const TrendingUp = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
  </svg>
)
const Truck = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 014 0m6 0a2 2 0 104 0m-4 0a2 2 0 014 0" />
  </svg>
)
const Shield = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
)

const FEATURES: Feature[] = [
  {
    icon: <BarChart2 />,
    title: 'Executive Command Center',
    description: 'Real-time dashboard showing total sales, receivables, payables, cash balance, inventory value, and operational pipeline — all in one view.',
    tag: 'Dashboard',
    tagColor: 'blue',
  },
  {
    icon: <Package />,
    title: 'Steel Inventory Intelligence',
    description: 'Track every SKU across MT, KG, and PCS. Low-stock alerts, valuation at cost or selling price, and warehouse-level grouping built-in.',
    tag: 'Inventory',
    tagColor: 'emerald',
  },
  {
    icon: <FileText />,
    title: 'Order & Document Pipeline',
    description: 'Quotations, Sales Orders, Purchase Orders, and Invoices flow seamlessly from creation to dispatch. Status transitions with one click.',
    tag: 'Operations',
    tagColor: 'violet',
  },
  {
    icon: <TrendingUp />,
    title: 'Financial Command',
    description: 'Track outstanding receivables, supplier payables, cash vault and bank balances. Mark invoices paid and watch cash flow update instantly.',
    tag: 'Finance',
    tagColor: 'amber',
  },
  {
    icon: <Truck />,
    title: 'Dispatch & Delivery Tracking',
    description: "Monitor orders through Pending → In Production → Ready for Dispatch → Delivered. Today's deliveries and overdue shipments surfaced immediately.",
    tag: 'Logistics',
    tagColor: 'cyan',
  },
  {
    icon: <Shield />,
    title: 'Built for Indian Trade',
    description: 'Rupee-native financials, mill-grade product taxonomy, GST-ready invoicing, and WhatsApp order parsing — built for how Indian traders actually work.',
    tag: 'Local-First',
    tagColor: 'rose',
  },
]

const tagStyles: Record<string, string> = {
  blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  violet: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
  amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  rose: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
}

const iconStyles: Record<string, string> = {
  blue: 'bg-blue-500/10 text-blue-400',
  emerald: 'bg-emerald-500/10 text-emerald-400',
  violet: 'bg-violet-500/10 text-violet-400',
  amber: 'bg-amber-500/10 text-amber-400',
  cyan: 'bg-cyan-500/10 text-cyan-400',
  rose: 'bg-rose-500/10 text-rose-400',
}

const FeaturesSection: React.FC = () => {
  return (
    <section id="features" className="relative py-28 bg-[#080c14]">
      {/* Subtle top separator line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <div className="section-label mb-4">
            <span className="w-4 h-px bg-blue-400 inline-block" />
            Platform Features
            <span className="w-4 h-px bg-blue-400 inline-block" />
          </div>
          <h2 className="text-4xl lg:text-5xl font-black text-white tracking-tight mb-4">
            Everything you need to run a{' '}
            <span className="gradient-text-blue">steel trading</span> business
          </h2>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto">
            From floor orders to financial reporting — GMTOOLS gives you complete operational visibility without the enterprise complexity.
          </p>
        </div>

        {/* Feature grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((feature, i) => (
            <div
              key={feature.title}
              className="feature-card glass-card rounded-2xl p-6 cursor-default"
              style={{ animationDelay: `${i * 0.08}s` }}
            >
              <div className="flex items-start justify-between mb-5">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${iconStyles[feature.tagColor]}`}>
                  {feature.icon}
                </div>
                <span className={`px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider border ${tagStyles[feature.tagColor]}`}>
                  {feature.tag}
                </span>
              </div>
              <h3 className="text-base font-bold text-white mb-2.5">{feature.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default FeaturesSection
