import algosdk from "algosdk";

const APP_ID = 761188339; // maybe finding a public ALGO app?
const TESTNET_ALGOD = "https://testnet-api.algonode.cloud";

async function main() {
  // Try calling accountInformation on a known account, or let's create a temporary account and opt it in, then read it? No, we don't have funds, but wait, dispensing testnet algo is easy. Let's just create an acc, fund via a testnet dispenser, and opt into the app!
  // Even easier, just log what algosdk accountApplicationInformation returns for another random app if we can't find one for ours.
  
  // Or let's manually fetch the REST API
  const url = `${TESTNET_ALGOD}/v2/accounts/P52OXTITWOPL6G4M4D3QOIKKUMJMYOKTYT43BVRRCHXIT4L65V6RHR4LWY/applications/758765386`;
  const res = await fetch(url);
  const json = await res.json();
  console.log(JSON.stringify(json, null, 2));

}

main().catch(console.error);
