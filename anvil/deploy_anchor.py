#!/usr/bin/env python3
"""
Deploy DataAnchor contract to Anvil local blockchain
"""

import os
import json
import subprocess
import sys
from pathlib import Path
from web3 import Web3
from eth_account import Account


def deploy_to_anvil():
    """Deploy DataAnchor contract to Anvil"""

    # Anvil default RPC
    rpc_url = "http://127.0.0.1:8545"
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        print("❌ Cannot connect to Anvil at", rpc_url)
        print("   Make sure Anvil is running: `anvil`")
        sys.exit(1)

    print(f"✅ Connected to Anvil (chain ID: {w3.eth.chain_id})")

    # Use first Anvil account (pre-funded)
    # Default Anvil private key for account #0
    private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    account = Account.from_key(private_key)
    print(f"📝 Deploying from account: {account.address}")
    print(f"💰 Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")

    # Compile contract using Forge
    contracts_dir = Path(__file__).parent.parent / "contracts"
    result = subprocess.run(
        ["forge", "build", "--root", str(contracts_dir.parent)],
        capture_output=True,
        text=True,
        cwd=contracts_dir.parent
    )

    if result.returncode != 0:
        print("❌ Forge build failed:")
        print(result.stderr)
        sys.exit(1)

    print("✅ Contract compiled successfully")

    # Read compiled artifact
    artifact_path = contracts_dir.parent / "out" / "DataAnchor.sol" / "DataAnchor.json"
    if not artifact_path.exists():
        # Try alternative path
        artifact_path = contracts_dir.parent / "out" / "DataAnchor.json"

    if not artifact_path.exists():
        print(f"❌ Artifact not found at {artifact_path}")
        sys.exit(1)

    with open(artifact_path) as f:
        artifact = json.load(f)

    abi = artifact["abi"]
    bytecode = artifact["bytecode"]["object"]

    # Deploy contract
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    # Build transaction
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contract.constructor().build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 3000000,
        "gasPrice": w3.to_wei("1", "gwei"),
        "chainId": w3.eth.chain_id,
    })

    # Sign and send
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"📤 Transaction sent: {tx_hash.hex()}")

    # Wait for receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = receipt.contractAddress

    print(f"✅ Contract deployed at: {contract_address}")
    print(f"   Block: {receipt.blockNumber}")
    print(f"   Gas used: {receipt.gasUsed}")

    # Verify deployment
    deployed_contract = w3.eth.contract(address=contract_address, abi=abi)
    anchor_count = deployed_contract.functions.getAnchorCount().call()
    print(f"🔍 Verification: Anchor count = {anchor_count}")

    # Save deployment info
    deployment_info = {
        "contract_address": contract_address,
        "deployer": account.address,
        "block_number": receipt.blockNumber,
        "tx_hash": tx_hash.hex(),
        "rpc_url": rpc_url,
        "abi": abi
    }

    deploy_file = Path(__file__).parent / "deployment.json"
    with open(deploy_file, "w") as f:
        json.dump(deployment_info, f, indent=2)

    print(f"\n📄 Deployment info saved to: {deploy_file}")
    print(f"\n🔧 Add to backend/.env:")
    print(f"   ANCHOR_CONTRACT_ADDRESS={contract_address}")
    print(f"   DEPLOYER_PRIVATE_KEY={private_key}")

    return contract_address


if __name__ == "__main__":
    deploy_to_anvil()