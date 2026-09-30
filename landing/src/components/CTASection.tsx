import React from 'react'

const CTASection: React.FC = () => {
  return (
    <section id="pricing" className="relative py-28 overflow-hidden bg-[#080c14]">
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

      {/* Ambient glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-blue-600/8 blur-[80px] rounded-full pointer-events-none" />

      <div className="max-w-4xl mx-auto px-6 lg:px-8 text-center relative z-10">
        <div className="section-label mb-6 justify-center">
          <span className="w-4 h-px bg-blue-400 inline-block" />
          Get Started
          <span className="w-4 h-px bg-blue-400 inline-block" />
        </div>

        <h2 className="text-4xl lg:text-6xl font-black text-white tracking-tight mb-6 leading-[1.05]">
          Ready to command your
          <br />
          <span className="gradient-text-blue">operations?</span>
        </h2>

        <p className="text-slate-400 text-lg mb-10 max-w-2xl mx-auto">
          GMTOOLS is deployed and ready. Sign in to your Command Center and take full control of your steel trading or manufacturing business — today.
        </p>

        {/* Single CTA */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
          <a
            href="http://localhost:5000/login"
            className="btn-primary text-base px-10 py-4 shadow-2xl shadow-blue-500/25"
          >
            Launch GMTOOLS
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5-5 5M6 12h12" />
            </svg>
          </a>
          <a
            href="http://localhost:5000/register"
            className="btn-secondary text-base px-10 py-4"
          >
            Create Account
          </a>
        </div>

        {/* Trust badges */}
        <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-slate-500">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            No setup fees
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            Instant access
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            Data seeded with real steel SKUs
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            Login: admin / admin123
          </div>
        </div>
      </div>
    </section>
  )
}

export default CTASection
