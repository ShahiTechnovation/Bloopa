/**
 * App.jsx — Main application shell for Bloopa.
 *
 * Pages:
 *   1. Landing Page  — marketing/hero page (default for new visitors)
 *   2. App Shell     — Register OR Dashboard/Score (for connected users)
 *
 * Routing logic:
 *   - No wallet → Landing Page (or app if user clicked "Launch App")
 *   - Wallet connected, fetching → Loading spinner (prevents false Register flash)
 *   - Wallet connected, stake > 0 → Dashboard/Score tabs
 *   - Wallet connected, stake === 0 → Register page
 */

import React, { useState, useEffect } from "react";
import { useWallet } from "./context/WalletContext.jsx";
import { useContract } from "./context/ContractContext.jsx";
import Header from "./components/Header.jsx";
import Footer from "./components/Footer.jsx";
import TabBar from "./components/TabBar.jsx";
import LandingPage from "./components/LandingPage.jsx";
import Register from "./components/Register.jsx";
import Dashboard from "./components/Dashboard.jsx";
import ScoreView from "./components/ScoreView.jsx";
import DocsShell from "./components/Docs/DocsShell.jsx";



function LoadingSpinner() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "60vh",
        gap: "16px",
      }}
    >
      <div
        style={{
          width: 40,
          height: 40,
          borderRadius: "50%",
          border: "3px solid var(--bg-elevated)",
          borderTop: "3px solid var(--accent)",
          animation: "spin 0.8s linear infinite",
        }}
      />
      <p
        style={{
          fontFamily: "var(--font-sans)",
          fontSize: 13,
          color: "var(--text-muted)",
          letterSpacing: "0.08em",
        }}
      >
        LOADING POSITION…
      </p>
    </div>
  );
}

export default function App() {
  const { address } = useWallet();
  const { position, loading } = useContract();
  const [activeTab, setActiveTab] = useState("position");
  const [view, setView] = useState("landing"); // 'landing', 'app', 'docs'

  // Track whether we've completed at least one position fetch for this address
  const [hasFetched, setHasFetched] = useState(false);

  const isRegistered = position.stake > 0n;

  // Auto-switch to app when wallet connects
  useEffect(() => {
    if (address && view === "landing") {
      setView("app");
      setHasFetched(false); // reset for new address
    } else if (!address) {
      setHasFetched(false);
    }
  }, [address, view]);

  // Mark fetch complete once loading becomes false after connecting
  useEffect(() => {
    if (address && !loading) {
      setHasFetched(true);
    }
  }, [address, loading]);

  // While wallet is connected but we haven't finished first fetch, show spinner
  const showLoading = view === "app" && address && !hasFetched && loading;

  return (
    <div className="min-h-screen flex flex-col font-body bg-transparent">
      <Header 
        onLogoClick={() => setView("landing")} 
        onAppClick={() => setView("app")}
        onDocsClick={() => setView("docs")}
        activeView={view}
      />

      <main
        className="flex-1 w-full"
        style={{ paddingTop: "100px", paddingBottom: "32px" }}
      >
        {view === "docs" ? (
          <DocsShell />
        ) : view === "landing" ? (
          <LandingPage onLaunchApp={() => setView("app")} />
        ) : showLoading ? (
          <LoadingSpinner />
        ) : !address || !isRegistered ? (
          <div className="max-w-[960px] mx-auto px-4 md:px-6 py-4">
            <Register />
          </div>
        ) : (
          <div className="max-w-[960px] mx-auto px-4 md:px-6">
            {/* Tab bar */}
            <div className="card overflow-hidden mb-6 mt-4 rounded-[12px]">
              <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
            </div>

            {/* Tab content */}
            {activeTab === "position" && <Dashboard />}
            {activeTab === "score" && <ScoreView />}
          </div>
        )}
      </main>


      <Footer />
    </div>
  );
}
