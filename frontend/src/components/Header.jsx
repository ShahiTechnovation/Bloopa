/**
 * Header.jsx — Fixed top navigation bar.
 *
 * Left:   Bloopa logo (hand drawn style SVG) + "Bloopa"
 * Center: Network pill — green dot + "ALGORAND TESTNET"
 * Right:  Connect button or address pill + disconnect
 */

import React, { useState, useEffect } from "react";
import { useWallet } from "../context/WalletContext.jsx";
import { fmtAddress } from "../utils/format.js";
import { algodClient } from "../utils/algod.js";

function LogoMark() {
  return (
    <div className="w-8 h-8 bg-warning border-[3px] border-black shadow-brutalist-sm rotate-3 flex items-center justify-center font-bold text-xl">
      B*
    </div>
  );
}

function DisconnectIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <path d="M6 2H4a2 2 0 00-2 2v8a2 2 0 002 2h2M10.5 11.5L14 8l-3.5-3.5M14 8H6"/>
    </svg>
  );
}

export default function Header({ onLogoClick }) {
  const { address, connectPera, connectDefly, disconnect } = useWallet();
  const [showWalletMenu, setShowWalletMenu] = useState(false);
  const [balance, setBalance] = useState(null);

  // Fetch ALGO balance
  useEffect(() => {
    if (!address) { setBalance(null); return; }
    const fetchBal = async () => {
      try {
        const info = await algodClient.accountInformation(address).do();
        setBalance((Number(info.amount) / 1e6).toFixed(2));
      } catch {}
    };
    fetchBal();
    const iv = setInterval(fetchBal, 15000);
    return () => clearInterval(iv);
  }, [address]);

  // Close menu on outside click
  useEffect(() => {
    if (!showWalletMenu) return;
    const handler = () => setShowWalletMenu(false);
    setTimeout(() => document.addEventListener("click", handler), 0);
    return () => document.removeEventListener("click", handler);
  }, [showWalletMenu]);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 p-2 md:p-4 md:px-6 pointer-events-none">
      <div className="max-w-[1240px] mx-auto pointer-events-auto h-16 bg-white border-[3px] border-black shadow-brutalist flex items-center justify-between px-3 md:px-5">
        
        {/* Left — Logo */}
        <button
          onClick={onLogoClick}
          className="flex items-center gap-3 active:translate-y-[2px] transition-transform duration-75"
        >
          <LogoMark />
          <span className="font-display font-black text-2xl tracking-tight text-black pt-1">
            Bloopa
          </span>
        </button>

        {/* Center — Network pill */}
        <div className="hidden sm:flex items-center gap-2 px-4 py-1 bg-accent-dim border-[2px] border-black shadow-brutalist-sm rotate-[-1deg] font-pixel text-lg">
          <span className="w-2.5 h-2.5 rounded-full bg-success border border-black animate-pulse" />
          <span className="uppercase text-black font-bold pt-1">
            Algorand Testnet
          </span>
        </div>

        {/* Right — Wallet */}
        <div className="flex items-center gap-2">
          {address ? (
            <>
              {/* Balance */}
              {balance && (
                <span className="hidden md:inline font-pixel font-bold text-lg text-black bg-white px-2 border-2 border-black rotate-1">
                  {balance} ALGO
                </span>
              )}
              {/* Address pill */}
              <div className="flex items-center gap-2 px-3 py-1 bg-white border-[2.5px] border-black shadow-brutalist-sm -rotate-1 cursor-default">
                <span className="w-2 h-2 rounded-full bg-success border border-black" />
                <span className="font-pixel font-bold text-lg text-black pt-1">
                  {fmtAddress(address)}
                </span>
              </div>
              {/* Disconnect */}
              <button
                id="wallet-disconnect"
                onClick={disconnect}
                className="w-10 h-10 flex items-center justify-center bg-danger-dim border-[2.5px] border-black shadow-brutalist-sm brutalist-btn text-black"
                title="Disconnect wallet"
              >
                <DisconnectIcon />
              </button>
            </>
          ) : (
            <div className="relative">
              <button
                id="wallet-connect"
                onClick={() => setShowWalletMenu(!showWalletMenu)}
                className="h-10 px-6 bg-accent border-[3px] border-black shadow-brutalist hover:bg-accent-hover active:translate-y-[2px] active:translate-x-[2px] active:shadow-brutalist-sm transition-all duration-75 font-display font-black text-sm uppercase tracking-wide text-black"
              >
                Connect Wallet
              </button>
              {showWalletMenu && (
                <div
                  className="absolute right-0 top-full mt-3 w-52 bg-white border-[3px] border-black shadow-brutalist p-2 z-50"
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    id="wallet-connect-pera"
                    onClick={() => { connectPera(); setShowWalletMenu(false); }}
                    className="w-full text-left px-3 py-2.5 border-[2px] border-transparent hover:border-black font-display font-bold text-sm uppercase text-black hover:bg-warning-dim flex items-center gap-3 transition-colors mb-1"
                  >
                    <span className="w-6 h-6 flex items-center justify-center text-xs font-black bg-[#ffee55] border-[2px] border-black">P</span>
                    Pera Wallet
                  </button>
                  <button
                    id="wallet-connect-defly"
                    onClick={() => { connectDefly(); setShowWalletMenu(false); }}
                    className="w-full text-left px-3 py-2.5 border-[2px] border-transparent hover:border-black font-display font-bold text-sm uppercase text-black hover:bg-accent-dim flex items-center gap-3 transition-colors"
                  >
                    <span className="w-6 h-6 flex items-center justify-center text-xs font-black bg-[#5eead4] border-[2px] border-black">D</span>
                    Defly Wallet
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
