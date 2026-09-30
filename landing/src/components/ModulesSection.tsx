import React from 'react'

interface Module {
  title: string
  description: string
  items: string[]
  icon: string
  gradient: string
  borderColor: string
}

const MODULES: Module[] = [
  {
    title: 'Sales & Revenue',
    description: 'Complete sales lifecycle management',
    icon: '📈',
    gradient: 'from-blue-500/5 to-transparent',
    borderColor: 'border-blue-500/15',
    items: [
      'Create & manage quotations',
      'Sales order booking',
      'Invoice generation',
      'Direct sales transactions',
      'WhatsApp order parsing',
      'Monthly revenue analytics',
    ],
  },
  {
    title: 'Procurement',
    description: 'End-to-end purchasing workflow',
    icon: '🏭',
    gradient: 'from-violet-500/5 to-transparent',
    borderColor: 'border-violet-500/15',
    items: [
      'Purchase order management',
      'Supplier database & balances',
      'Receipt tracking',
      'Outstanding payables view',
      'Mill-grade supplier profiles',
      'PO-to-receipt reconciliation',
    ],
  },
  {
    title: 'Inventory',
    description: 'Real-time stock intelligence',
    icon: '📦',
    gradient: 'from-emerald-500/5 to-transparent',
    borderColor: 'border-emerald-500/15',
    items: [
      'Multi-unit tracking (MT/KG/PCS)',
      'Category & parent grouping',
      'Cost price vs selling price',
      'Low-stock alert thresholds',
      'Real-time inventory valuation',
      'SKU-level product taxonomy',
    ],
  },
  {
    title: 'Finance & Cash',
    description: 'Complete financial command',
    icon: '💰',
    gradient: 'from-amber-500/5 to-transparent',
    borderColor: 'border-amber-500/15',
    items: [
      'Cash & bank account tracking',
      'Outstanding receivables',
      'Invoice payment marking',
      'Overdue payment alerts',
      'Cash flow visibility',
      'Customer balance ledger',
    ],
  },
]

const ModulesSection: React.FC = () => {
  return (
    <section id="modules" className="relative py-28 bg-[#080c14]">
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="text-center mb-16">
          <div className="section-label mb-4">
            <span className="w-4 h-px bg-blue-400 inline-block" />
            Business Modules
            <span className="w-4 h-px bg-blue-400 inline-block" />
          </div>
          <h2 className="text-4xl lg:text-5xl font-black text-white tracking-tight mb-4">
            Four modules.{' '}
            <span className="gradient-text-blue">One command center.</span>
          </h2>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto">
            GMTOOLS brings together every aspect of your trading business — all connected, all real-time.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {MODULES.map((mod) => (
            <div
              key={mod.title}
              className={`relative rounded-2xl border ${mod.borderColor} overflow-hidden bg-gradient-to-b ${mod.gradient} feature-card cursor-default`}
            >
              <div className="p-6">
                <div className="text-3xl mb-4">{mod.icon}</div>
                <h3 className="text-base font-bold text-white mb-1">{mod.title}</h3>
                <p className="text-xs text-slate-500 mb-5">{mod.description}</p>

                <ul className="space-y-2">
                  {mod.items.map((item) => (
                    <li key={item} className="flex items-start gap-2 text-xs text-slate-400">
                      <svg className="w-3.5 h-3.5 text-blue-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default ModulesSection
