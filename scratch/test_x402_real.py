import os
import logging
from dotenv import load_dotenv
from bloopa_sdk import BloopaCreditAgent, BloopX402Client

logging.basicConfig(level=logging.INFO)
load_dotenv()

agent = BloopaCreditAgent(
    mnemonic_phrase=os.environ["AGENT_MNEMONIC"],
    app_id=int(os.environ["BLOOPA_APP_ID"]),
    usdc_app_id=int(os.environ["USDC_APP_ID"]),
    demo_mode=True
)

client = BloopX402Client(agent)
print("Sending request to x402 endpoint...")
try:
    resp = client.get("https://x402.goplausible.xyz/examples/weather")
    print("STATUS:", resp.status_code)
    print("TEXT:", resp.text)
except Exception as e:
    print("ERROR:", e)
