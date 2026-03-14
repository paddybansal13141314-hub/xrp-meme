import json
import os
from pathlib import Path

from xrpl.wallet import Wallet


def main():
    issuer = Wallet.create()
    hot = Wallet.create()

    out_file = Path(os.getenv("WALLET_OUT", "xrpascend_mainnet_wallets.json")).resolve()
    payload = {
        "issuer": {
            "classic_address": issuer.classic_address,
            "seed": issuer.seed,
        },
        "hot": {
            "classic_address": hot.classic_address,
            "seed": hot.seed,
        },
    }
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Saved mainnet wallet seeds to: {out_file}")
    print("Fund these two addresses with XRP before launching:")
    print(f"ISSUER_ADDRESS={issuer.classic_address}")
    print(f"HOT_ADDRESS={hot.classic_address}")
    print("Then set ISSUER_SEED and HOT_SEED as environment variables and run launch_xrpascend.py with XRPL_NETWORK=mainnet.")


if __name__ == "__main__":
    main()
