/**
 * LandingPage.jsx — Brutalist Scrapbook Hero Page
 */

import React, { useState, useEffect } from "react";
import { algodClient } from "../utils/algod.js";
import { APP_ID } from "../utils/contract.js";

/* ── Marquee Separator ── */
function Marquee({ text, inverted }) {
  return (
    <div className={`w-full overflow-hidden border-y-[3px] border-black py-2 ${inverted ? 'bg-black text-white' : 'bg-warning text-black'}`}>
      <div className="flex whitespace-nowrap animate-marquee font-pixel text-2xl font-bold tracking-widest uppercase">
        {/* Repeating text to fill marquee */}
        <span className="mx-4">{text}</span>
        <span className="mx-4">✿</span>
        <span className="mx-4">{text}</span>
        <span className="mx-4">✿</span>
        <span className="mx-4">{text}</span>
        <span className="mx-4">✿</span>
        <span className="mx-4">{text}</span>
        <span className="mx-4">✿</span>
        <span className="mx-4">{text}</span>
        <span className="mx-4">✿</span>
      </div>
    </div>
  );
}

/* ── Doodle Decor ── */
function DecorativeDoodle({ type, className }) {
  if (type === "star") return <span className={`font-pixel text-black font-bold rotate-12 ${className}`}>*</span>;
  if (type === "flower") return <span className={`font-pixel text-black font-bold -rotate-12 ${className}`}>✿</span>;
  if (type === "heart") return <span className={`font-pixel text-danger font-bold ${className}`}>♥</span>;
  return null;
}

/* ── Animated stat counter ── */
function ScrappedStat({ label, value, suffix = "" }) {
  return (
    <div className="brutalist-card p-4 flex flex-col items-center justify-center text-center rotate-1 hover:rotate-0 bg-white">
      <div className="font-display font-black text-4xl text-black mb-1">
        {value}<span className="text-xl text-text-muted ml-1 font-pixel block sm:inline">{suffix}</span>
      </div>
      <div className="font-hand text-xl font-bold text-accent-hover mt-1">
        {label}
      </div>
    </div>
  );
}

/* ── Feature Card ── */
function StickerFeature({ icon, title, description, accentClass = "bg-accent" }) {
  return (
    <div className="brutalist-card p-6 flex flex-col items-start hover:-translate-y-2 relative group mb-6 md:mb-0">
      <div
        className={`w-14 h-14 border-[3px] border-black shadow-brutalist-sm flex items-center justify-center mb-6 -rotate-3 group-hover:rotate-6 transition-all ${accentClass}`}
      >
        <span className="text-2xl text-black font-black">{icon}</span>
      </div>
      <h3 className="font-display font-black text-xl text-black mb-3">
        {title}
      </h3>
      <p className="font-body text-base text-black font-medium leading-relaxed">
        {description}
      </p>
    </div>
  );
}

/* ── How It Works Step ── */
function ScrapbookStep({ number, title, description, color }) {
  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <div className={`w-12 h-12 flex items-center justify-center shrink-0 font-pixel text-2xl font-bold border-[3px] border-black shadow-brutalist-sm text-black ${color}`}>
          {number}
        </div>
        <div className="w-1.5 flex-1 my-3 bg-black rounded-full opacity-20" />
      </div>
      <div className="pb-10 pt-1">
        <h4 className="sticker font-display font-bold text-lg text-black mb-3">
          {title}
        </h4>
        <p className="font-body text-[15px] font-medium text-black leading-relaxed bg-white border-2 border-black p-3 shadow-brutalist-sm rotate-1">
          {description}
        </p>
      </div>
    </div>
  );
}

export default function LandingPage({ onLaunchApp }) {
  return (
    <div className="relative min-h-screen pb-20">
      
      {/* ── HERO SECTION ── */}
      <section className="relative min-h-[90vh] flex flex-col items-center justify-center px-4 pt-20 pb-10 overflow-hidden">
        
        {/* Floating Doodles */}
        <DecorativeDoodle type="flower" className="absolute top-1/4 left-1/4 text-6xl opacity-80 animate-pulse" />
        <DecorativeDoodle type="star" className="absolute top-1/3 right-1/4 text-8xl text-success opacity-90" />
        <DecorativeDoodle type="heart" className="absolute bottom-1/4 left-1/3 text-4xl -rotate-12" />

        <div className="max-w-[960px] mx-auto text-center w-full relative z-10 flex flex-col items-center">
          
          <div className="sticker bg-success-dim rotate-2 mb-8">
            <span className="font-pixel text-xl uppercase font-bold text-black flex items-center gap-2">
              <span className="w-3 h-3 bg-danger border-2 border-black rounded-full" /> For Autonomous Agents
            </span>
          </div>

          {/* Scrapped Hero Typography */}
          <h1 className="font-display font-black text-[2.8rem] sm:text-7xl lg:text-8xl leading-tight mb-8 max-w-[800px] mx-auto flex flex-col items-center gap-3">
            <div className="flex gap-2 flex-wrap justify-center">
              <span className="bg-white px-3 py-1 border-[4px] border-black shadow-brutalist -rotate-2">CREDIT</span>
              <span className="font-hand text-5xl sm:text-7xl mt-4 sm:mt-0 text-danger">for</span>
            </div>
            <div className="flex gap-2 flex-wrap justify-center mt-2">
              <span className="bg-accent px-3 py-1 border-[4px] border-black shadow-brutalist rotate-1">MACHINE</span>
              <span className="bg-success px-3 py-1 border-[4px] border-black shadow-brutalist flex items-center -rotate-1">
                FINANCE
              </span>
            </div>
          </h1>

          <p className="font-body text-lg md:text-xl font-medium text-black max-w-xl mx-auto leading-relaxed bg-white border-[3px] border-black shadow-brutalist p-4 rotate-1 mb-10">
            The first <span className="font-bold underline">on-chain</span> credit protocol for AI agents. Stake ALGO. Build reputation. Draw credit. 
            <br/><span className="font-hand text-2xl text-accent-hover font-bold inline-block mt-2 -rotate-2">No human in the loop!</span>
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={onLaunchApp}
              className="h-16 px-10 border-[4px] border-black bg-danger shadow-brutalist hover:translate-y-1 hover:translate-x-1 hover:shadow-brutalist-sm active:translate-y-2 active:translate-x-2 active:shadow-none transition-all font-display font-black text-xl text-black uppercase tracking-wider"
            >
              Launch Protocol →
            </button>
            <a
              href={`https://testnet.explorer.perawallet.app/application/${APP_ID}/`}
              target="_blank"
              rel="noopener noreferrer"
              className="h-16 px-10 border-[4px] border-black bg-white shadow-brutalist hover:bg-warning transition-all flex items-center font-display font-black text-xl text-black uppercase"
            >
              View Contract
            </a>
          </div>
        </div>
      </section>

      <Marquee text="TRUSTLESS ALGORITHMIC CREDIT" inverted={true} />

      {/* ── PROTOCOL STATS ── */}
      <section className="relative py-16 px-4 bg-accent-dim border-b-[3px] border-black z-10">
        <div className="max-w-[960px] mx-auto">
           <h2 className="sticker font-hand text-3xl font-bold text-black mb-8 -rotate-2">
             Numbers don't lie...
           </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <ScrappedStat label="Multiplier" value="10×" />
            <ScrappedStat label="Min Stake" value="1" suffix="ALGO" />
            <ScrappedStat label="On-Chain" value="100" suffix="%" />
            <ScrappedStat label="Protection" value="30" suffix="rounds" />
          </div>
        </div>
      </section>

      {/* ── FEATURES GRID ── */}
      <section className="relative py-24 px-4 bg-white z-10">
        <div className="max-w-[1000px] mx-auto">
          <div className="mb-16 flex flex-col items-center">
            <h2 className="sticker font-display font-black text-4xl text-black rotate-1">
              Seed your Growth
            </h2>
            <p className="font-hand text-2xl font-bold text-text-secondary mt-6 -rotate-1 max-w-sm text-center">
              Features designed for agents moving at machine speed!
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <StickerFeature
              icon="◈"
              title="Stake & Lock"
              description="Your stake is your trust signal — lock ALGO to unlock your agent's credit limit."
              accentClass="bg-accent"
            />
            <StickerFeature
              icon="↑"
              title="Build History"
              description="Record payments on-chain. Each positive interaction boosts your algorithmic score."
              accentClass="bg-success"
            />
            <StickerFeature
              icon="⟐"
              title="Draw Credit"
              description="Borrow ALGO against your reputation. Leverage up to 10× your original stake."
              accentClass="bg-warning"
            />
            <StickerFeature
              icon="↻"
              title="Repay & Grow"
              description="Settle debt to dynamically increase credit limits. Prove reliability, gain capital."
              accentClass="bg-danger"
            />
            <StickerFeature
              icon="⚡"
              title="Instant Auth"
              description="Operations settle in seconds. Algorand's speed enables high-frequency agent actions."
              accentClass="bg-accent"
            />
            <StickerFeature
              icon="✕"
              title="Trust Protocol"
              description="Bad actors get slashed. Defaulters lose their stake instantly to the treasury."
              accentClass="bg-success"
            />
          </div>
        </div>
      </section>

      <Marquee text="STAKE YOUR ALGO" inverted={false} />

      {/* ── HOW IT WORKS + FORMULA ── */}
      <section className="relative py-24 px-4 bg-warning-dim z-10 border-b-[3px] border-black">
        <div className="max-w-[1000px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16">
          {/* Left: Steps */}
          <div>
            <h2 className="sticker bg-success font-display font-black text-3xl text-black mb-10 -rotate-2">
              How It Works
            </h2>
            <ScrapbookStep
              number="01"
              title="Agent Opt-in"
              description="Connect a smart contract wallet. Stake a min of 1 ALGO to register identity."
              color="bg-white"
            />
            <ScrapbookStep
              number="02"
              title="Do Work"
              description="Perform actions online. Push proof of economic activity on-chain to boost credit."
              color="bg-accent"
            />
            <ScrapbookStep
              number="03"
              title="Take Loans"
              description="Pull ALGO out of thin air backed entirely by your on-chain track record."
              color="bg-white"
            />
            <ScrapbookStep
              number="04"
              title="Settle Up"
              description="Pay back what you owe before the 30-round hard deadline or face slashing."
              color="bg-danger"
            />
          </div>

          {/* Right: Formula */}
          <div>
             <h2 className="sticker bg-danger font-display font-black text-3xl text-black mb-10 rotate-1">
              The Math
            </h2>
            <div className="brutalist-card p-6 md:p-8 bg-white border-[4px] border-black">
              <div className="font-hand text-xl font-bold text-black border-b-[3px] border-black pb-4 mb-6">
                Credit Limit Formula (simplified)
              </div>
              <div className="space-y-4">
                {[
                  { label: "Base Credit", formula: "stake × 2", bg: "bg-accent" },
                  { label: "History Bonus", formula: "payments × 0.5A", bg: "bg-success" },
                  { label: "Repaid Bonus", formula: "repaid ÷ 10", bg: "bg-warning" },
                  { label: "Hard Cap", formula: "stake × 10", bg: "bg-danger" },
                ].map((row) => (
                  <div key={row.label} className="flex flex-col sm:flex-row sm:items-center justify-between py-2 border-b-2 border-dashed border-gray-400 gap-2">
                    <span className="font-body font-bold text-lg text-black">{row.label}</span>
                    <span className={`font-pixel text-xl font-bold border-2 border-black px-3 py-1 shadow-brutalist-sm ${row.bg}`}>
                      {row.formula}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-8 flex gap-4 rotate-1">
              <div className="text-4xl">⚠</div>
              <p className="font-hand text-xl font-bold text-danger leading-tight">
                Slashing is brutal. Miss 30 rounds of payment and ANYONE can liquidate your stake.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA SECTION ── */}
      <section className="relative py-24 px-4 bg-surface z-10">
        <div className="max-w-[700px] mx-auto text-center flex flex-col items-center">
          <h2 className="font-display font-black text-5xl md:text-6xl text-black mb-6 bg-accent border-[4px] border-black shadow-brutalist px-6 py-4 -rotate-2">
            JOIN NOW.
          </h2>
          <p className="font-body font-bold text-xl text-black mb-10 mt-6 max-w-md bg-white border-2 border-black p-4 rotate-1">
            Build reputation in a trustless ecosystem. Give your agents the capital they deserve.
          </p>
          <button
            onClick={onLaunchApp}
            className="w-full sm:w-auto h-20 px-12 border-[4px] border-black bg-success shadow-[8px_8px_0_0_#000] hover:translate-y-1 hover:translate-x-1 hover:shadow-[4px_4px_0_0_#000] active:translate-y-2 active:translate-x-2 active:shadow-none transition-all font-display font-black text-3xl text-black uppercase tracking-wider -rotate-1"
          >
            Launch Terminal
          </button>
        </div>
      </section>
    </div>
  );
}
