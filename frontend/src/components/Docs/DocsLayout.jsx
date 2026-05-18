/**
 * DocsLayout.jsx — Three-column premium docs shell.
 * Matches the stunning neo-brutalist Bloopa docs screenshot exactly.
 * Left: Scrollable search-enabled brutalist sidebar nav with slanted active buttons.
 * Center: Max 800px center scrollable content column.
 * Right: Sticky 220px Table of Contents (TOC) with page anchors and Discord support card.
 */

import React, { useState, useEffect } from "react";

// Navigation Groups matching the user's gorgeous mockup
const NAV_GROUPS = [
  {
    title: "GETTING STARTED",
    isHighlighted: false,
    items: [
      { id: "introduction", label: "Quickstart", icon: "bolt" },
      { id: "installation", label: "Installation", icon: "install_desktop" }
    ]
  },
  {
    title: "PROTOCOL",
    isHighlighted: false,
    items: [
      { id: "protocol", label: "Architecture", icon: "architecture" },
      { id: "security-model", label: "Security Model", icon: "security" }
    ]
  },
  {
    title: "SDK REFERENCE",
    isHighlighted: true, // Slanted yellow header sticker
    items: [
      { id: "sdk", label: "BloopaCreditAgent", icon: "code_blocks", hasSubMenu: true },
      { id: "wallet-manager", label: "WalletManager", icon: "account_balance_wallet" }
    ]
  },
  {
    title: "CONTRACT INTERFACE",
    isHighlighted: false,
    items: [
      { id: "abi", label: "TEAL / ABI Specs", icon: "article" },
      { id: "guides", label: "Guides & Safety", icon: "explore" }
    ]
  }
];

// Dynamic Table of Contents (TOC) matching each page's actual heading sections
const TOC_MAP = {
  introduction: [
    { label: "What is Bloopa?", href: "#what-is-bloopa" },
    { label: "Live Simulation", href: "#live-sim" },
    { label: "Protocol Stats", href: "#protocol-stats" }
  ],
  quickstart: [
    { label: "Prerequisites", href: "#prerequisites" },
    { label: "Step 1. Clone SDK", href: "#clone-sdk" },
    { label: "Step 2. Environment", href: "#setup-env" },
    { label: "Step 3. Run Demo", href: "#run-demo" }
  ],
  installation: [
    { label: "Installation", href: "#install-top" },
    { label: "Pip Package", href: "#pip-package" },
    { label: "Optional Extras", href: "#optional-extras" },
    { label: "Verification", href: "#verify-install" }
  ],
  protocol: [
    { label: "Economic Engine", href: "#core-engine" },
    { label: "State Transitions", href: "#states" },
    { label: "Credit Grades", href: "#credit-grades" }
  ],
  "security-model": [
    { label: "Trust Engine", href: "#trust-engine" },
    { label: "How It Works", href: "#how-it-works" },
    { label: "Oracle Response", href: "#oracle-response" },
    { label: "Signature Verification", href: "#sig-verification" }
  ],
  sdk: [
    { label: "Constructor", href: "#constructor" },
    { label: "Methods Overview", href: "#methods" },
    { label: "draw()", href: "#draw", isSub: true },
    { label: "repay()", href: "#repay", isSub: true },
    { label: "slash()", href: "#slash", isSub: true },
    { label: "get_position()", href: "#get_position", isSub: true }
  ],
  "wallet-manager": [
    { label: "WalletManager", href: "#wm-top" },
    { label: "Initialization", href: "#wm-init" },
    { label: "Account Control", href: "#wm-control" },
    { label: "Signing Transactions", href: "#wm-signing" }
  ],
  abi: [
    { label: "TEAL Interface", href: "#teal-top" },
    { label: "ABI Specifications", href: "#abi-specs" },
    { label: "State Schema", href: "#state-schema" }
  ],
  guides: [
    { label: "Safety Guides", href: "#guides-top" },
    { label: "Avoiding Liquidation", href: "#avoiding-liquidation" },
    { label: "Changelog", href: "#changelog" }
  ]
};

export default function DocsLayout({ activePage, onNavigate, children }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Auto-scroll to hash when loaded/navigated
  useEffect(() => {
    if (window.location.hash) {
      const id = window.location.hash.substring(1);
      const element = document.getElementById(id);
      if (element) {
        setTimeout(() => {
          element.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 100);
      }
    }
  }, [activePage]);

  // Handle Search Filtering
  const filteredGroups = NAV_GROUPS.map((group) => {
    const items = group.items.filter((item) =>
      item.label.toLowerCase().includes(searchQuery.toLowerCase())
    );
    return { ...group, items };
  }).filter((group) => group.items.length > 0);

  const tocItems = TOC_MAP[activePage] || [];

  return (
    <div style={{ display: "flex", minHeight: "calc(100vh - 80px)", position: "relative", background: "#FDFBF7", color: "#1b1b1b" }}>
      
      {/* ── Mobile hamburger ── */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        style={{
          display: "none",
          position: "fixed",
          bottom: 20,
          right: 20,
          zIndex: 200,
          width: 48,
          height: 48,
          background: "#FDE047",
          border: "3px solid #000",
          boxShadow: "4px 4px 0 #000",
          cursor: "pointer",
          fontFamily: "var(--font-display)",
          fontWeight: 900,
          fontSize: 20,
        }}
        className="docs-mobile-fab brutal-active"
        aria-label="Toggle docs navigation"
      >
        ☰
      </button>

      {/* ── Sidebar ── */}
      <aside
        style={{
          width: 280,
          minWidth: 280,
          background: "#ffffff",
          borderRight: "3px solid #000",
          position: "sticky",
          top: 80,
          height: "calc(100vh - 80px)",
          overflowY: "auto",
          flexShrink: 0,
          zIndex: 10,
          display: "flex",
          flexDirection: "column",
          padding: "24px",
        }}
        className="docs-sidebar"
      >
        {/* Search Input Box */}
        <div className="mb-8">
          <div className="relative brutal-shadow brutal-border bg-[#FDFBF7]">
            <span className="material-symbols-outlined absolute left-3 top-3 text-black text-[20px]">search</span>
            <input
              className="w-full bg-transparent border-none pl-10 pr-4 py-3 font-label-mono text-[12px] focus:ring-0 focus:outline-none placeholder-black text-black"
              placeholder="Search Docs..."
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Hierarchical Navigation list */}
        <div className="flex flex-col gap-6 font-label-mono text-[12px] text-black">
          {filteredGroups.map((group) => (
            <div key={group.title}>
              {/* Group Title Badge */}
              {group.isHighlighted ? (
                <div className="text-black mb-2 font-bold tracking-widest bg-yellow inline-block px-2 py-1 brutal-border transform rotate-1 text-[11px]">
                  {group.title}
                </div>
              ) : (
                <div className="text-gray-500 mb-2 font-bold tracking-widest text-[11px]">
                  {group.title}
                </div>
              )}

              {/* Group Items */}
              <div className="flex flex-col gap-1 mt-1">
                {group.items.map((item) => {
                  const isActive = activePage === item.id;
                  
                  if (isActive && item.hasSubMenu) {
                    // Selected highlighted badge link (e.g. BloopaCreditAgent in Python reference)
                    return (
                      <div key={item.id} className="flex flex-col gap-1">
                        <button
                          onClick={() => onNavigate(item.id)}
                          className="py-2 px-3 flex items-center gap-2 bg-mint brutal-border shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] -translate-x-1 -translate-y-1 font-bold text-black text-left w-full cursor-pointer"
                        >
                          <span className="material-symbols-outlined text-[16px]">{item.icon}</span>
                          {item.label}
                        </button>
                        
                        {/* Sub Menu Links */}
                        <div className="flex flex-col gap-1 ml-6 mt-1 text-[11px] text-gray-700">
                          <a className="hover:text-black hover:underline py-1 transition-all" href="#constructor">constructor</a>
                          <a className="hover:text-black hover:underline py-1 transition-all" href="#draw">draw()</a>
                          <a className="hover:text-black hover:underline py-1 transition-all" href="#repay">repay()</a>
                          <a className="hover:text-black hover:underline py-1 transition-all" href="#slash">slash()</a>
                          <a className="hover:text-black hover:underline py-1 transition-all" href="#get_position">get_position()</a>
                          <a className="text-red-600 hover:underline py-1 font-bold transition-all" href="#exceptions">BloopaCreditDenied</a>
                        </div>
                      </div>
                    );
                  }

                  // Standard navigation links
                  return (
                    <button
                      key={item.id}
                      onClick={() => {
                        onNavigate(item.id);
                        setMobileOpen(false);
                      }}
                      className="py-2 px-3 flex items-center gap-2 transition-all w-full text-left cursor-pointer font-label-mono text-[12px]"
                      style={{
                        background: isActive ? "#FDE047" : "transparent",
                        border: isActive ? "2px solid #000" : "2px solid transparent",
                        boxShadow: isActive ? "2px 2px 0px 0px rgba(0,0,0,1)" : "none",
                        fontWeight: isActive ? "bold" : "normal",
                        color: "#000",
                        transform: isActive ? "rotate(-1deg)" : "none"
                      }}
                    >
                      <span className="material-symbols-outlined text-[16px]">{item.icon}</span>
                      {item.label}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </aside>

      {/* ── Main Layout Wrapper ── */}
      <main style={{ flex: 1, display: "flex", minWidth: 0 }}>
        {/* Center Column for actual documentation content */}
        <div style={{ flex: 1, maxWidth: 800, padding: "48px", minWidth: 0 }} className="docs-center-content">
          {children}
        </div>

        {/* Right Sticky TOC (Desktop Only) */}
        {tocItems.length > 0 && (
          <aside
            style={{
              width: 220,
              minWidth: 220,
              padding: "48px 24px 24px 24px",
              position: "sticky",
              top: 80,
              height: "calc(100vh - 80px)",
              overflowY: "auto",
            }}
            className="hidden lg:block docs-toc"
          >
            <div className="font-label-mono text-[12px] font-bold mb-4 border-b-2 border-black pb-2 text-black select-none">
              ON THIS PAGE
            </div>
            
            <ul className="font-body-md text-[13px] space-y-3 list-none p-0 m-0">
              {tocItems.map((toc) => (
                <li key={toc.href} style={{ paddingLeft: toc.isSub ? 12 : 0, borderLeft: toc.isSub ? "2px solid #e5e5e5" : "none" }}>
                  <a
                    className="hover:text-mint hover:underline hover:bg-black hover:px-1 py-0.5 text-gray-700 transition-all block text-ellipsis overflow-hidden whitespace-nowrap"
                    href={toc.href}
                  >
                    {toc.label}
                  </a>
                </li>
              ))}
            </ul>

            {/* Premium Discord Help Widget */}
            <div className="mt-12 bg-white brutal-border p-4 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] rotate-2">
              <div className="font-label-mono text-[10px] font-bold mb-2 text-black">NEED HELP?</div>
              <p className="text-[11px] mb-3 text-gray-700 leading-normal">Join the builders in our Discord for SDK support.</p>
              <button 
                onClick={() => window.open("#", "_blank")}
                className="w-full bg-black text-white font-label-mono py-2 text-[10px] brutal-hover brutal-active brutal-border border-black cursor-pointer uppercase font-bold"
              >
                DISCORD -&gt;
              </button>
            </div>
          </aside>
        )}
      </main>

      {/* Mobile Responsiveness Rules */}
      <style>{`
        @media (max-width: 768px) {
          .docs-mobile-fab { display: flex !important; align-items: center; justify-content: center; }
          .docs-sidebar {
            display: ${mobileOpen ? "flex" : "none"} !important;
            position: fixed !important;
            top: 56px !important;
            left: 0;
            width: 100% !important;
            height: calc(100vh - 56px) !important;
            z-index: 150;
            border-right: none !important;
          }
          .docs-center-content { padding: 24px 20px !important; }
        }
      `}</style>
    </div>
  );
}
