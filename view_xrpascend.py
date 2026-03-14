import json
import os
from pathlib import Path

from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountLines

DEFAULT_SUMMARY_FILE = "xrpascend_launch_output.json"
TESTNET_RPC = "https://s.altnet.rippletest.net:51234"
MAINNET_RPC = "https://xrplcluster.com"


def main():
    summary_file = Path(os.getenv("XRPASCEND_SUMMARY_FILE", DEFAULT_SUMMARY_FILE)).resolve()
    if not summary_file.exists():
        raise RuntimeError(f"Launch summary file not found: {summary_file}")

    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    network = summary["network"]
    rpc = summary["network_rpc"] or (MAINNET_RPC if network == "mainnet" else TESTNET_RPC)
    client = JsonRpcClient(rpc)

    response = client.request(
        AccountLines(
            account=summary["hot_address"],
            peer=summary["issuer_address"],
        )
    )
    if not response.is_successful():
        raise RuntimeError(
            f"Could not fetch token line. status={response.status}, result={response.result}"
        )

    token_line = next(
        (
            line
            for line in response.result.get("lines", [])
            if line.get("currency") == summary["token_code_hex"]
        ),
        None,
    )

    output = {
        "network": network,
        "token_name": summary["token_name"],
        "token_symbol": summary["token_symbol"],
        "token_code_hex": summary["token_code_hex"],
        "issuer": summary["issuer_address"],
        "hot_wallet": summary["hot_address"],
        "hot_wallet_balance": token_line.get("balance") if token_line else None,
        "explorer_links": summary.get("explorer_links", {}),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
