/**
 * Footer.jsx — Fixed bottom status bar.
 *
 * Left:   Live round number from algodClient.status()
 * Center: App ID with explorer link
 * Right:  Treasury balance (placeholder until global state read)
 */

import React, { useState, useEffect, useRef } from "react";
import { algodClient } from "../utils/algod.js";
import { APP_ID } from "../utils/contract.js";
import { fmtRound } from "../utils/format.js";

export default function Footer() {
  const [round, setRound] = useState(null);
  const [pulsing, setPulsing] = useState(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const status = await algodClient.status().do();
        const r = status["last-round"];
        setRound(r);
        // Trigger pulse
        setPulsing(true);
        setTimeout(() => setPulsing(false), 1000);
      } catch (err) {
        console.log("Footer status fetch:", err.message);
      }
    };

    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, 10000);
    return () => clearInterval(intervalRef.current);
  }, []);

  return (
    <footer className="fixed bottom-0 left-0 right-0 z-40 p-2 md:p-4 px-4 pointer-events-none">
      <div className="max-w-[1240px] mx-auto pointer-events-auto h-10 bg-white border-[3px] border-black shadow-brutalist flex items-center justify-between px-4">
        {/* Left — Round number */}
        <span
          className="font-pixel text-lg text-black font-bold flex items-center gap-2"
          style={{
            opacity: pulsing ? 1 : 0.6,
            transition: "opacity 0.2s"
          }}
        >
          <span className={`w-2 h-2 rounded-full border border-black ${pulsing ? 'bg-success' : 'bg-gray-200'}`}></span>
          {round ? `ROUND ${fmtRound(round)}` : "CONNECTING..."}
        </span>

        {/* Center — App ID */}
        <a
          href={`https://testnet.explorer.perawallet.app/application/${APP_ID}/`}
          target="_blank"
          rel="noopener noreferrer"
          className="font-pixel text-lg text-black font-bold flex items-center gap-1 hover:bg-warning px-2 border-2 border-transparent hover:border-black transition-all"
        >
          APP {APP_ID}
        </a>

        {/* Right — Network indicator */}
        <span className="font-pixel text-lg text-black font-bold hidden sm:block bg-accent-dim border-[2px] border-black px-2 shadow-brutalist-sm rotate-1">
          ALGORAND TESTNET
        </span>
      </div>
    </footer>
  );
}
