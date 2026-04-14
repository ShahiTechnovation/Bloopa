/**
 * Register.jsx — Agent registration & staking interface.
 */

import React, { useState } from "react";
import { useWallet } from "../context/WalletContext.jsx";
import { useContract } from "../context/ContractContext.jsx";
import { useToast } from "./ui/Toast.jsx";

/* ── Decorative components ── */
function DecorativeDoodle({ type, className }) {
  if (type === "star") return <span className={`font-pixel text-black font-bold rotate-12 ${className}`}>*</span>;
  if (type === "flower") return <span className={`font-pixel text-black font-bold -rotate-12 ${className}`}>✿</span>;
  if (type === "heart") return <span className={`font-pixel text-danger font-bold ${className}`}>♥</span>;
  return null;
}

function WalletIcon() {
  return (
    <div className="w-16 h-16 bg-accent border-[3px] border-black shadow-brutalist-sm rotate-3 flex items-center justify-center -mb-2 z-10">
       <span className="text-3xl">👛</span>
    </div>
  );
}

function StepIndicator({ currentStep }) {
  const steps = [
    { num: 1, label: "Opt-in" },
    { num: 2, label: "Stake" },
    { num: 3, label: "Active" },
  ];
  return (
    <div className="flex items-center justify-center gap-2 my-4">
      {steps.map((step, i) => {
        const isCompleted = currentStep > step.num;
        const isCurrent = currentStep === step.num;
        return (
          <React.Fragment key={step.num}>
            <div className="flex flex-col items-center gap-1">
              <div
                className={`w-10 h-10 border-[3px] border-black shadow-brutalist-sm flex items-center justify-center font-pixel text-xl font-bold transition-all ${
                  isCompleted || isCurrent ? "bg-warning rotate-3" : "bg-white -rotate-3"
                }`}
              >
                {isCompleted ? "✓" : step.num}
              </div>
              <span className={`font-hand text-lg font-bold ${isCurrent ? "text-black" : "text-gray-400"}`}>
                {step.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className="w-10 h-1 bg-black opacity-20 -mt-6" />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

export default function Register() {
  const { address, connectPera, connectDefly } = useWallet();
  const { callRegister, loading, isOptedIn } = useContract();
  const { addToast } = useToast();
  const [stakeInput, setStakeInput] = useState("1");
  const [txStatus, setTxStatus] = useState("idle"); // idle | signing | submitting | confirming | success | error
  const [errorMsg, setErrorMsg] = useState("");

  const stakeValue = parseFloat(stakeInput) || 0;
  const isValid = stakeValue >= 1;
  const initialCredit = (stakeValue * 2).toFixed(6);
  const maxCredit = (stakeValue * 10).toFixed(6);

  const handleRegister = async () => {
    if (!isValid) return;
    setTxStatus("signing");
    setErrorMsg("");
    try {
      setTxStatus("submitting");
      await callRegister(stakeInput);
      setTxStatus("success");
      addToast(`✓ Agent registered — Initial credit: ${initialCredit} ALGO`, "success", 5000);
    } catch (err) {
      setTxStatus("error");
      setErrorMsg(err.message);
      addToast(err.message, "error");
    }
  };

  const getButtonText = () => {
    switch (txStatus) {
      case "signing": return "Signing...";
      case "submitting": return "Sending...";
      case "confirming": return "Confirm...";
      default: return "Register →";
    }
  };

  const currentStep = !address ? 1 : txStatus === "success" ? 3 : 2;

  const fmtAddress = (addr, start, end) => {
    if (!addr) return "";
    return `${addr.substring(0, start)}...${addr.substring(addr.length - end)}`;
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-10rem)] px-4 py-10 relative overflow-hidden">
      
      {/* Background Doodles */}
      <DecorativeDoodle type="star" className="absolute top-10 left-10 text-6xl text-success" />
      <DecorativeDoodle type="flower" className="absolute bottom-20 right-10 text-8xl text-warning" />

      {/* Hero title */}
      <div className="text-center mb-12 max-w-xl flex flex-col items-center">
        <h1 className="font-display font-black text-5xl md:text-7xl leading-tight mb-4 flex flex-wrap justify-center gap-x-4">
           <span className="bg-white border-[4px] border-black shadow-brutalist px-4 py-1 -rotate-2 text-black">CREDIT</span>
           <span className="font-hand text-danger text-4xl mt-4">for</span>
           <span className="bg-accent border-[4px] border-black shadow-brutalist px-4 py-1 rotate-1 mt-2 text-black">AGENTS</span>
        </h1>
        <p className="font-hand text-2xl font-bold text-black mt-4 -rotate-1 bg-white border-2 border-dashed border-black px-4 py-1">
          Stake. Build history. Unlock finance!
        </p>
      </div>

      {/* Registration card */}
      <div
        className="brutalist-card w-full max-w-[460px] p-0 relative overflow-hidden"
        style={{ transform: txStatus === "success" ? "rotate(0deg)" : "rotate(1deg)" }}
      >
        <div className="bg-white p-8 flex flex-col items-center">
          
          {/* Stage 1: Connect wallet */}
          {!address && (
            <div className="flex flex-col items-center text-center">
              <WalletIcon />
              <h2 className="sticker bg-warning font-display font-black text-2xl text-black my-5">
                IDENTIFY SELF
              </h2>
              <p className="font-body font-bold text-black mb-8 px-4">
                Pera or Defly Wallet required for on-chain identity.
              </p>
              <div className="w-full flex flex-col gap-4">
                <button
                  id="register-connect-pera"
                  onClick={connectPera}
                  className="h-14 bg-[#ffee55] border-[3px] border-black shadow-brutalist-sm brutalist-btn flex items-center justify-center gap-3 font-display font-black text-sm uppercase text-black"
                >
                  <span className="w-8 h-8 flex items-center justify-center text-xs font-black bg-white border-2 border-black">P</span>
                  Connect Pera Wallet
                </button>
                <button
                  id="register-connect-defly"
                  onClick={connectDefly}
                  className="h-14 bg-[#5eead4] border-[3px] border-black shadow-brutalist-sm brutalist-btn flex items-center justify-center gap-3 font-display font-black text-sm uppercase text-black"
                >
                  <span className="w-8 h-8 flex items-center justify-center text-xs font-black bg-white border-2 border-black">D</span>
                  Connect Defly Wallet
                </button>
              </div>
            </div>
          )}

          {/* Stage 2: Stake form */}
          {address && txStatus !== "success" && (
            <div className="w-full flex flex-col gap-6">
              {/* Connected address */}
              <div className="flex items-center gap-3 px-4 py-2 bg-success-dim border-[3px] border-black shadow-brutalist-sm -rotate-1">
                <span className="w-3 h-3 rounded-full bg-success border-2 border-black animate-pulse" />
                <span className="font-pixel text-lg font-bold text-black truncate pt-1">
                  {fmtAddress(address, 6, 6)}
                </span>
                {isOptedIn && (
                  <span className="ml-auto font-pixel text-xs bg-white border-2 border-black px-1.5 pt-0.5 text-black">
                    OPTED IN
                  </span>
                )}
              </div>

              <div className="flex flex-col gap-2">
                <label className="font-display font-black text-lg uppercase text-black">Stake Amount</label>
                <div className="relative">
                  <input
                    id="stake-input"
                    type="number"
                    value={stakeInput}
                    onChange={(e) => setStakeInput(e.target.value)}
                    className="w-full h-14 bg-white border-[3px] border-black shadow-brutalist-sm px-4 font-pixel text-2xl font-bold focus:bg-warning-dim transition-colors text-black"
                    placeholder="1.000000"
                  />
                  <span className="absolute right-4 top-3.5 font-pixel text-xl font-bold opacity-50 text-black">ALGO</span>
                </div>
                {!isValid && stakeInput !== "" && (
                  <p className="font-hand text-lg font-bold text-danger">Min 1 ALGO required!</p>
                )}
              </div>

              {/* Live credit preview */}
              <div className="bg-accent-dim border-[3px] border-black p-4 space-y-3 rotate-1">
                <div className="flex items-center justify-between border-b-2 border-black border-dashed pb-2">
                  <span className="font-body font-bold text-sm text-black">Initial Credit</span>
                  <span className="font-pixel text-xl font-bold text-black">{initialCredit} ALGO</span>
                </div>
                <div className="flex items-center justify-between border-b-2 border-black border-dashed pb-2">
                  <span className="font-body font-bold text-sm text-black">Max Credit</span>
                  <span className="font-pixel text-xl font-bold text-black">{maxCredit} ALGO</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-body font-bold text-sm text-black">Multiplier</span>
                  <span className="bg-white border-2 border-black px-2 font-pixel text-xl font-bold text-black">2× → 10×</span>
                </div>
              </div>

              <StepIndicator currentStep={currentStep} />

              <button
                id="register-button"
                disabled={!isValid || loading || txStatus !== "idle"}
                onClick={handleRegister}
                className="h-16 w-full bg-success border-[3px] border-black shadow-brutalist hover:translate-x-1 hover:translate-y-1 hover:shadow-brutalist-sm disabled:opacity-50 disabled:translate-x-0 disabled:translate-y-0 disabled:shadow-brutalist-sm transition-all font-display font-black text-xl uppercase tracking-widest text-black"
              >
                 {loading || txStatus !== "idle" ? getButtonText() : "Register Agent →"}
              </button>

              {/* Error */}
              {errorMsg && (
                <div className="bg-danger border-[3px] border-black p-4 flex items-start gap-3 -rotate-1 text-black">
                  <span className="text-xl">✕</span>
                  <p className="font-pixel text-lg font-bold uppercase">
                    Error: {errorMsg}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Stage 3: Success */}
          {txStatus === "success" && (
            <div className="flex flex-col items-center text-center py-6">
              <div className="w-20 h-20 bg-success border-[4px] border-black shadow-brutalist flex items-center justify-center mb-6 rotate-6">
                <span className="text-5xl text-black">✓</span>
              </div>
              <h2 className="sticker bg-success font-display font-black text-3xl text-black mb-4">
                AGENT ACTIVE
              </h2>
              <div className="bg-white border-[3px] border-black p-6 shadow-brutalist -rotate-2">
                <p className="font-hand text-2xl font-bold text-black mb-1">
                  Initial Credit Limit
                </p>
                <p className="font-pixel text-4xl font-black text-black">
                  {initialCredit} ALGO
                </p>
              </div>
              <p className="font-hand text-2xl font-bold text-accent-hover mt-8 animate-pulse">
                Redirecting to Terminal...
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Info cards below registration */}
      {!address && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mt-16 max-w-[700px] w-full">
          {[
            { icon: "◈", title: "Stake & Lock", desc: "Lock ALGO to build trust.", color: "bg-accent" },
            { icon: "↑", title: "Build History", desc: "Record payments for score.", color: "bg-success" },
            { icon: "⟐", title: "Draw Credit", desc: "Borrow up to 10× stake.", color: "bg-warning" },
          ].map((f) => (
            <div key={f.title} className="brutalist-card p-5 bg-white flex flex-col items-center text-center group">
              <div className={`w-12 h-12 border-[2px] border-black shadow-brutalist-sm ${f.color} flex items-center justify-center mb-3 rotate-3 group-hover:-rotate-6 transition-transform`}>
                 <span className="text-xl text-black">{f.icon}</span>
              </div>
              <h3 className="font-display font-black text-base text-black mb-2 uppercase">{f.title}</h3>
              <p className="font-body text-sm font-semibold text-black leading-snug">{f.desc}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
