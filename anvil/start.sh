#!/bin/bash
# Start Anvil local blockchain

echo "🚀 Starting Anvil local blockchain..."
echo "   RPC URL: http://127.0.0.1:8545"
echo "   Chain ID: 31337"
echo ""
echo "Pre-funded accounts (10000 ETH each):"
echo "  Account #0: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
echo "  Private Key: 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
echo ""
echo "Press Ctrl+C to stop"
echo ""

anvil --host 0.0.0.0 --port 8545 --chain-id 31337