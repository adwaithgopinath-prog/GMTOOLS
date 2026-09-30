import React from 'react'

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t border-white/[0.06] bg-[#080c14] py-12">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-black text-white text-sm shadow-lg shadow-blue-500/20">
              GM
            </div>
            <div>
              <div className="font-bold text-white text-sm tracking-tight">GMTOOLS</div>
              <div className="text-[10px] text-slate-600">Industrial ERP Platform</div>
            </div>
          </div>

          {/* Links */}
          <div className="flex items-center gap-6 text-sm text-slate-500">
            <a href="#features" className="hover:text-slate-300 transition-colors">Features</a>
            <a href="#platform" className="hover:text-slate-300 transition-colors">Platform</a>
            <a href="#modules" className="hover:text-slate-300 transition-colors">Modules</a>
            <a href="http://localhost:5000/login" className="hover:text-slate-300 transition-colors">Login</a>
          </div>

          {/* Copyright */}
          <div className="text-xs text-slate-600">
            © {currentYear} GMTOOLS. All rights reserved.
          </div>
        </div>

        {/* Bottom tagline */}
        <div className="mt-8 pt-6 border-t border-white/[0.04] text-center">
          <p className="text-xs text-slate-700">
            Built for the Indian steel & cutting-tool industry · Flask · SQLite · Python
          </p>
        </div>
      </div>
    </footer>
  )
}

export default Footer
