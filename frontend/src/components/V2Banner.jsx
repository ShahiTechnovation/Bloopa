import React from 'react';

export default function V2Banner() {
  return (
    <a
      href="https://v2.bloopa.xyz"
      target="_blank"
      rel="noopener noreferrer"
      className="block w-full bg-[#0a0a0a] text-white border-b-2 border-[#1a1a1a] cursor-pointer group transition-all duration-300 hover:bg-[#111111] pointer-events-auto"
      style={{
        textDecoration: 'none'
      }}
    >
      <div className="max-w-[1240px] mx-auto px-4 py-2.5 md:py-3 flex items-center justify-between">
        
        {/* Left: V2 Indicator */}
        <div className="hidden sm:flex items-center gap-2.5">
          <div className="flex items-center justify-center w-6 h-6 rounded bg-[#1a1a1a] border border-[#333] group-hover:border-[var(--accent)]/40 transition-colors">
            <span className="font-pixel text-[var(--accent)] text-xs">V2</span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[var(--accent)]/10 border border-[var(--accent)]/20 shadow-[0_0_8px_rgba(187,247,208,0.1)] group-hover:shadow-[0_0_12px_rgba(187,247,208,0.2)] transition-shadow">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse" />
            <span className="font-mono text-[10px] text-[var(--accent)] tracking-wider uppercase font-bold">Live</span>
          </div>
        </div>

        {/* Center: Main Copy */}
        <div className="flex-1 flex flex-col sm:flex-row items-center justify-center gap-1 sm:gap-3 text-center">
          <span className="font-display font-black text-sm md:text-base tracking-wide text-white group-hover:text-[var(--accent)] transition-colors drop-shadow-sm">
            BLOOPA V2 IS LIVE <span className="inline-block hover:scale-110 transition-transform">💚</span>
          </span>
          <span className="hidden sm:inline text-[#444] text-sm">|</span>
          <span className="font-body text-xs md:text-sm text-[#888] group-hover:text-[#aaa] transition-colors">
            Early Access is officially open.
          </span>
        </div>

        {/* Right: CTA */}
        <div className="hidden sm:flex items-center gap-2 text-[var(--accent)] font-display font-bold text-xs md:text-sm tracking-wider uppercase group-hover:text-white transition-colors drop-shadow-sm">
          <span>Enter V2</span>
          <span className="transform group-hover:translate-x-1.5 transition-transform duration-300">→</span>
        </div>

        {/* Mobile CTA Icon */}
        <div className="flex sm:hidden items-center text-[var(--accent)] group-hover:translate-x-1 transition-transform duration-300">
          <span className="font-bold">→</span>
        </div>

      </div>
    </a>
  );
}
