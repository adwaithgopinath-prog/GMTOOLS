import React, { useState } from 'react'

// Dashboard preview — a visual mockup of the GMTOOLS Command Center
// Built entirely in HTML/CSS (no images needed)

const METRIC_CARDS = [
  { label: 'Total Sales', value: '₹44.2L', change: '+12.4%', up: true, color: 'emerald' },
  { label: 'Outstanding Rec.', value: '₹14.85L', change: 'Due', up: false, color: 'amber' },
  { label: 'Cash + Bank', value: '₹20.25L', change: 'Available', up: true, color: 'blue' },
  { label: 'Inventory Value', value: '₹1.2Cr', change: '87 MT', up: true, color: 'violet' },
]

const ORDER_PIPELINE = [
  { status: 'Pending', count: 2, color: 'amber' },
  { status: 'In Production', count: 2, color: 'blue' },
  { status: 'Ready', count: 2, color: 'emerald' },
  { status: "Today's Delivery", count: 4, color: 'cyan' },
]

const RECENT_TXN = [
  { ref: 'SO-8901', party: 'Apex Infrastructure', amount: '₹8.1L', type: 'Sale', color: 'emerald' },
  { ref: 'PO-7021', party: 'Tata Steel Ltd', amount: '₹25.5L', type: 'Purchase', color: 'indigo' },
  { ref: 'INV-2026-1042', party: 'Apex Infrastructure', amount: '₹4.2L', type: 'Overdue', color: 'rose' },
]

const colorMap: Record<string, { dot: string; bg: string; text: string; border: string }> = {
  emerald: { dot: 'bg-emerald-400', bg: 'bg-emerald-400/10', text: 'text-emerald-400', border: 'border-emerald-400/20' },
  amber: { dot: 'bg-amber-400', bg: 'bg-amber-400/10', text: 'text-amber-400', border: 'border-amber-400/20' },
  blue: { dot: 'bg-blue-400', bg: 'bg-blue-400/10', text: 'text-blue-400', border: 'border-blue-400/20' },
  violet: { dot: 'bg-violet-400', bg: 'bg-violet-400/10', text: 'text-violet-400', border: 'border-violet-400/20' },
  cyan: { dot: 'bg-cyan-400', bg: 'bg-cyan-400/10', text: 'text-cyan-400', border: 'border-cyan-400/20' },
  indigo: { dot: 'bg-indigo-400', bg: 'bg-indigo-400/10', text: 'text-indigo-400', border: 'border-indigo-400/20' },
  rose: { dot: 'bg-rose-400', bg: 'bg-rose-400/10', text: 'text-rose-400', border: 'border-rose-400/20' },
}

// Tiny inline bar chart
const MiniBarChart: React.FC = () => {
  const bars = [62, 75, 68, 82, 71, 88, 95]
  return (
    <div className="flex items-end gap-1 h-12">
      {bars.map((h, i) => (
        <div key={i} className="flex-1 rounded-sm bg-blue-500/20 relative overflow-hidden" style={{ height: `${h}%` }}>
          <div className="absolute inset-0 bg-blue-400/40" />
        </div>
      ))}
    </div>
  )
}

const DashboardPreview: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'inventory' | 'orders'>('dashboard')

  return (
    <section id="platform" className="relative py-24 bg-[#080c14] overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

      {/* Ambient glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] bg-blue-600/5 blur-[100px] rounded-full pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="text-center mb-12">
          <div className="section-label mb-4">
            <span className="w-4 h-px bg-blue-400 inline-block" />
            Live Platform Preview
            <span className="w-4 h-px bg-blue-400 inline-block" />
          </div>
          <h2 className="text-4xl lg:text-5xl font-black text-white tracking-tight mb-4">
            Your operations at a glance
          </h2>
          <p className="text-slate-400 text-lg max-w-xl mx-auto">
            The Command Center shows you everything happening right now — no digging through reports.
          </p>
        </div>

        {/* Browser chrome mockup */}
        <div className="glass-card rounded-2xl overflow-hidden shadow-2xl shadow-black/40 max-w-5xl mx-auto">
          {/* Browser bar */}
          <div className="flex items-center gap-3 px-4 py-3 bg-white/[0.03] border-b border-white/[0.06]">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-rose-500/60" />
              <div className="w-3 h-3 rounded-full bg-amber-500/60" />
              <div className="w-3 h-3 rounded-full bg-emerald-500/60" />
            </div>
            <div className="flex-1 flex items-center justify-center">
              <div className="bg-white/5 border border-white/10 rounded-md px-3 py-1 flex items-center gap-2 text-xs text-slate-500 font-mono w-48">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                localhost:5000
              </div>
            </div>
          </div>

          {/* App sidebar + content */}
          <div className="flex min-h-[460px]">
            {/* Sidebar */}
            <div className="hidden sm:flex flex-col w-14 bg-[#0a0f1e] border-r border-white/[0.05] py-4 items-center gap-3">
              {[
                { icon: '⊞', active: activeTab === 'dashboard', tab: 'dashboard' as const },
                { icon: '◫', active: activeTab === 'inventory', tab: 'inventory' as const },
                { icon: '⊠', active: activeTab === 'orders', tab: 'orders' as const },
              ].map((item, i) => (
                <button
                  key={i}
                  onClick={() => setActiveTab(item.tab)}
                  className={`w-8 h-8 rounded-lg text-sm flex items-center justify-center transition-all ${
                    item.active
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30'
                      : 'text-slate-500 hover:bg-white/5 hover:text-slate-300'
                  }`}
                >
                  {item.icon}
                </button>
              ))}
            </div>

            {/* Main content */}
            <div className="flex-1 p-4 bg-[#080c14] overflow-hidden">
              {activeTab === 'dashboard' && (
                <div className="space-y-3">
                  {/* Header */}
                  <div className="flex items-center justify-between mb-1">
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Floor Command</div>
                      <div className="text-sm font-bold text-white">Executive Command Center</div>
                    </div>
                    <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-medium">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      Live
                    </div>
                  </div>

                  {/* KPI Cards */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                    {METRIC_CARDS.map((m) => {
                      const c = colorMap[m.color]
                      return (
                        <div key={m.label} className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-2.5">
                          <div className="text-[9px] text-slate-500 uppercase tracking-wider font-bold mb-1">{m.label}</div>
                          <div className="text-base font-black text-white tabular-nums">{m.value}</div>
                          <div className={`text-[10px] font-semibold mt-1 ${c.text}`}>{m.change}</div>
                        </div>
                      )
                    })}
                  </div>

                  {/* Order Pipeline + Chart Row */}
                  <div className="grid grid-cols-5 gap-2">
                    {/* Pipeline */}
                    <div className="col-span-2 bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
                      <div className="text-[9px] text-slate-500 uppercase font-bold mb-2">Order Pipeline</div>
                      <div className="space-y-1.5">
                        {ORDER_PIPELINE.map((op) => {
                          const c = colorMap[op.color]
                          return (
                            <div key={op.status} className="flex items-center justify-between">
                              <div className="flex items-center gap-1.5">
                                <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
                                <span className="text-[10px] text-slate-400">{op.status}</span>
                              </div>
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${c.bg} ${c.text}`}>{op.count}</span>
                            </div>
                          )
                        })}
                      </div>
                    </div>

                    {/* Mini chart */}
                    <div className="col-span-3 bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-[9px] text-slate-500 uppercase font-bold">Sales 6-Month Trend</div>
                        <div className="text-[10px] text-blue-400 font-bold">₹ Lakhs</div>
                      </div>
                      <MiniBarChart />
                      <div className="flex justify-between mt-1">
                        {['N', 'D', 'J', 'F', 'M', 'A', 'Today'].map((l) => (
                          <span key={l} className="text-[9px] text-slate-600">{l}</span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Recent Transactions */}
                  <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
                    <div className="text-[9px] text-slate-500 uppercase font-bold mb-2">Recent Transactions</div>
                    <div className="space-y-1.5">
                      {RECENT_TXN.map((t) => {
                        const c = colorMap[t.color]
                        return (
                          <div key={t.ref} className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${c.bg} ${c.text} ${c.border}`}>{t.type}</span>
                              <span className="text-[10px] text-slate-400">{t.party}</span>
                            </div>
                            <span className="text-[10px] font-bold text-white">{t.amount}</span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'inventory' && (
                <div className="space-y-3">
                  <div className="text-sm font-bold text-white mb-3">Steel Inventory</div>
                  {[
                    { sku: 'ST-TMT-12MM', name: 'Fe 550D TMT Rebar 12mm', qty: 42, unit: 'MT', status: 'ok' },
                    { sku: 'ST-EN-24', name: 'EN 24 Alloy Steel Bar', qty: 3, unit: 'MT', status: 'low' },
                    { sku: 'ST-BEAM-300', name: 'MS Universal Beam ISMB 300', qty: 18, unit: 'MT', status: 'ok' },
                    { sku: 'ST-HR-04MM', name: 'Hot Rolled Sheet 4.0mm', qty: 2, unit: 'MT', status: 'low' },
                    { sku: 'ST-PIPE-100', name: 'MS Square Hollow Section 100x100', qty: 14, unit: 'MT', status: 'ok' },
                  ].map((item) => (
                    <div key={item.sku} className="flex items-center justify-between bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2.5">
                      <div>
                        <div className="text-[10px] text-slate-500 font-mono">{item.sku}</div>
                        <div className="text-xs text-white font-medium">{item.name}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-white tabular-nums">{item.qty} <span className="text-slate-500 text-xs">{item.unit}</span></span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${item.status === 'low' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'}`}>
                          {item.status === 'low' ? 'Low Stock' : 'In Stock'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === 'orders' && (
                <div className="space-y-3">
                  <div className="text-sm font-bold text-white mb-3">Sales Orders</div>
                  {[
                    { id: 'SO-8901', customer: 'Apex Infrastructure Ltd', product: '15 MT Fe 550D TMT Rebars 12mm', status: 'pending', amount: '₹8.1L' },
                    { id: 'SO-8898', customer: 'Vanguard Pre-Fab Structures', product: '12 MT EN 24 High Tensile Round Bar', status: 'in_production', amount: '₹8.16L' },
                    { id: 'SO-8892', customer: 'Royal Builders & EPC Projects', product: '10 MT Fe 550D TMT Rebar', status: 'ready', amount: '₹5.4L' },
                    { id: 'SO-8888', customer: 'Apex Infrastructure Ltd', product: '5 MT MS Universal Beam', status: 'delivered', amount: '₹2.8L' },
                  ].map((o) => {
                    const statusConfig: Record<string, { label: string; color: string }> = {
                      pending: { label: 'Pending', color: 'amber' },
                      in_production: { label: 'In Production', color: 'blue' },
                      ready: { label: 'Ready', color: 'emerald' },
                      delivered: { label: 'Delivered', color: 'slate' },
                    }
                    const sc = statusConfig[o.status]
                    const c = colorMap[sc.color] || colorMap.blue
                    return (
                      <div key={o.id} className="bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2.5">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[10px] font-mono text-slate-400">{o.id}</span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${c.bg} ${c.text} ${c.border}`}>{sc.label}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="text-xs text-white font-medium">{o.customer}</div>
                            <div className="text-[10px] text-slate-500">{o.product}</div>
                          </div>
                          <span className="text-sm font-bold text-white">{o.amount}</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Tab switcher hint */}
        <div className="flex items-center justify-center gap-4 mt-6">
          {(['dashboard', 'inventory', 'orders'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                activeTab === tab
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                  : 'bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white'
              }`}
            >
              {tab === 'dashboard' ? 'Command Center' : tab === 'inventory' ? 'Inventory' : 'Orders'}
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}

export default DashboardPreview
