import json
import os
from pathlib import Path

from xrpl.clients import JsonRpcClient
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.requests import AccountLines
from xrpl.models.transactions import AccountSet, AccountSetAsfFlag, Payment, TrustSet
from xrpl.transaction import submit_and_wait
from xrpl.utils import str_to_hex
from xrpl.wallet import Wallet, generate_faucet_wallet

TOKEN_NAME = "XRpepe"
TOKEN_SYMBOL = "XRPEPE"
TOKEN_SUPPLY = "1000000000"
TOKEN_CODE = (str_to_hex(TOKEN_SYMBOL).upper() + ("0" * 40))[:40]
DEFAULT_RPC = "https://s.altnet.rippletest.net:51234"


def submit_checked(client: JsonRpcClient, wallet: Wallet, tx):
    response = submit_and_wait(tx, client, wallet)
    tx_hash = response.result.get("hash")
    tx_result = response.result.get("meta", {}).get("TransactionResult")
    if not response.is_successful() or tx_result != "tesSUCCESS":
        raise RuntimeError(
            f"{tx.transaction_type} failed: status={response.status}, tx_result={tx_result}, hash={tx_hash}"
        )
    return tx_hash


def get_wallets(client: JsonRpcClient):
    issuer_seed = os.getenv("ISSUER_SEED")
    hot_seed = os.getenv("HOT_SEED")

    if issuer_seed and hot_seed:
        return Wallet.from_seed(issuer_seed), Wallet.from_seed(hot_seed), False

    if issuer_seed or hot_seed:
        raise RuntimeError("Set both ISSUER_SEED and HOT_SEED, or neither.")

    issuer_wallet = generate_faucet_wallet(client, usage_context="xrpepe-issuer")
    hot_wallet = generate_faucet_wallet(client, usage_context="xrpepe-hot")
    return issuer_wallet, hot_wallet, True


def save_wallets_if_generated(issuer_wallet: Wallet, hot_wallet: Wallet):
    out_path = Path(os.getenv("WALLET_OUT", "xrpepe_wallets.json")).resolve()
    payload = {
        "issuer": {
            "classic_address": issuer_wallet.classic_address,
            "seed": issuer_wallet.seed,
        },
        "hot": {
            "classic_address": hot_wallet.classic_address,
            "seed": hot_wallet.seed,
        },
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(out_path)


def main():
    rpc_url = os.getenv("XRPL_RPC", DEFAULT_RPC)
    client = JsonRpcClient(rpc_url)

    issuer_wallet, hot_wallet, generated = get_wallets(client)

    if generated:
        wallet_file = save_wallets_if_generated(issuer_wallet, hot_wallet)
        print(f"Saved generated wallet seeds to: {wallet_file}")

    set_default_ripple_hash = submit_checked(
        client,
        issuer_wallet,
        AccountSet(
            account=issuer_wallet.classic_address,
            set_flag=AccountSetAsfFlag.ASF_DEFAULT_RIPPLE,
        ),
    )

    trust_set_hash = submit_checked(
        client,
        hot_wallet,
        TrustSet(
            account=hot_wallet.classic_address,
            limit_amount=IssuedCurrencyAmount(
                currency=TOKEN_CODE,
                issuer=issuer_wallet.classic_address,
                value=TOKEN_SUPPLY,
            ),
        ),
    )

    issue_hash = submit_checked(
        client,
        issuer_wallet,
        Payment(
            account=issuer_wallet.classic_address,
            destination=hot_wallet.classic_address,
            amount=IssuedCurrencyAmount(
                currency=TOKEN_CODE,
                issuer=issuer_wallet.classic_address,
                value=TOKEN_SUPPLY,
            ),
        ),
    )

    lines_response = client.request(
        AccountLines(
            account=hot_wallet.classic_address,
            peer=issuer_wallet.classic_address,
        )
    )
    if not lines_response.is_successful():
        raise RuntimeError(
            f"Failed to fetch account lines: status={lines_response.status}, result={lines_response.result}"
        )

    token_line = next(
        (
            line
            for line in lines_response.result.get("lines", [])
            if line.get("currency") == TOKEN_CODE
        ),
        None,
    )

    summary = {
        "network_rpc": rpc_url,
        "token_name": TOKEN_NAME,
        "token_symbol": TOKEN_SYMBOL,
        "token_code_hex": TOKEN_CODE,
        "issued_supply": TOKEN_SUPPLY,
        "issuer_address": issuer_wallet.classic_address,
        "hot_address": hot_wallet.classic_address,
        "hot_wallet_token_balance": token_line.get("balance") if token_line else None,
        "tx_hashes": {
            "accountset_default_ripple": set_default_ripple_hash,
            "trustset_hot_wallet": trust_set_hash,
            "payment_issue_supply": issue_hash,
        },
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
