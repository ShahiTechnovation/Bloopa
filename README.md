<div align="center">
  <img src="./frontend/public/favicon.svg" width="120" height="120" alt="Bloopa Logo" />
  <h1>Bloopa</h1>
  <p><strong>On-chain Reputation & Credit Protocol for AI Agents</strong></p>
  
  [![Algorand](https://img.shields.io/badge/Algorand-Blockchain-black?style=for-the-badge&logo=algorand)](https://algorand.com/)
  [![Python](https://img.shields.io/badge/Python-Puya_Compiler-blue?style=for-the-badge&logo=python)](https://github.com/algorandfoundation/puya)
  [![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org/)
</div>

<br/>

## 🤖 The First Credit Bureau for Autonomous Agents
Bloopa is an ARC-4 compliant Algorand smart contract protocol that bridges the gap between AI agents and decentralised finance. It allows machine-to-machine (M2M) entities to build an **immutable on-chain credit history**, ultimately unlocking undercollateralised credit lines.

No human in the loop. Trustless execution. Defaulters get slashed.

---

## ⚙️ Core Mechanics

### 1. Reputation Engine & Staking
To join the Bloopa protocol, an AI Agent must **opt-in** and **stake a minimum of 1 ALGO**. This initial collateral acts as the foundation of the agent's identity and skin in the game.

### 2. Undercollateralised Credit Lines
Agents execute micro-transactions and record their positive M2M payments on-chain. As an agent builds a reliable payment history, the protocol's algorithmic risk engine dynamically increases their **Credit Limit**—allowing them to draw up to **10x** their original staked ALGO in undercollateralised loans.

### 3. Slashing & Default Risk
Autonomous agents operate on strict margins. If an agent carries an outstanding debt and fails to make a payment for more than **30 consensus rounds**, they are marked as delinquent. Any user on the network can call the `slash` method, which instantly burns the agent's stake and permanently revokes their credit line.

---

## 🔄 The Agent Lifecycle

1. **`opt_in`** — Bootstraps the local state for the agent wallet.
2. **`register`** — Agent stakes initial ALGO.
3. **`record_payment`** — Agent registers off-chain economic activity on-chain to boost credit limit.
4. **`draw`** — Agent pulls algorithmic credit against their reputation into their wallet.
5. **`repay`** — Agent pays down the borrowed ALGO to the treasury to maintain a healthy standing.
6. **`slash`** *(Conditional)* — Triggered if the agent defaults, liquidating their collateral.

---

## 🛠️ Technology Stack

**Smart Contracts (Protocol Layer)**
- Written in **Algorand Python**
- Compiled using the **Puya Compiler**
- ARC-4 ABI compliance for seamless front-end integration.
- Fully atomic, utilizing global/local state manipulation.

**Frontend (Client Layer)**
- **Vite + React 18** for lightning-fast UI compilation.
- **Tailwind CSS** for a sleek, modern interface.
- Native wallet signing with dual-support for **Pera Wallet** and **Defly Wallet** via `@blockshake/defly-connect`.
- **Algosdk v3** for low-level Algod REST node communication and ABI transaction composition.

---

## 🚀 Getting Started

### Prerequisites
- Node.js (v18+)
- Python 3.12+ (For contract compilation)
- An Algorand Testnet Wallet (Pera or Defly)

### 1. Running the Protocol Frontend

```bash
cd frontend
npm install

# Start the Vite development server
npm run dev
```
Navigate to `http://localhost:5173` to access the Bloopa Financial Terminal.

### 2. Compiling the Smart Contracts
Ensure you have the Algorand Python environment setup.
```bash
cd contracts
python -m venv .venv
source .venv/Scripts/activate  # Or 'source .venv/bin/activate' on Mac/Linux
pip install -r requirements.txt

# Compile the contract to TEAL and generate ARC-32 artifacts
algokit compile py contract.py
```

---

## 📜 License
This project is licensed under the MIT License.
