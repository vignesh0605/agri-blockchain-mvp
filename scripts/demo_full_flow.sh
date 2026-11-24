#!/bin/bash
# Full Demo Flow Script for Agri Supply Chain MVP

set -e  # Exit on error

echo "========================================="
echo "🌱 Agri Supply Chain MVP - Full Demo Flow"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${BLUE}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

# Check prerequisites
print_step "Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found. Please install Python 3.11+"
    exit 1
fi
print_success "Python 3 found"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    print_warning "Virtual environment not found. Creating..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate
print_success "Virtual environment activated"

# Install dependencies
print_step "Installing dependencies..."
pip install -q -r requirements.txt
print_success "Dependencies installed"

# Initialize database
print_step "Initializing database..."
python scripts/init_db.py
print_success "Database initialized"

# Generate sample data
print_step "Generating sample data..."
python scripts/generate_sample_data.py
print_success "Sample data generated"

# Check if Anvil is running
print_step "Checking Anvil connection..."
if curl -s -X POST -H "Content-Type: application/json" \
   --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
   http://127.0.0.1:8545 > /dev/null 2>&1; then
    print_success "Anvil is running"
else
    print_warning "Anvil not running. Please start it in another terminal:"
    echo "  cd anvil && ./start.sh"
    echo ""
    read -p "Press Enter after starting Anvil to continue..."
fi

# Deploy contract if not deployed
print_step "Checking contract deployment..."
if [ -f "anvil/deployment.json" ]; then
    CONTRACT_ADDRESS=$(cat anvil/deployment.json | python3 -c "import sys, json; print(json.load(sys.stdin)['contract_address'])")
    print_success "Contract already deployed at $CONTRACT_ADDRESS"
else
    print_step "Deploying DataAnchor contract..."
    python anvil/deploy_anchor.py
    CONTRACT_ADDRESS=$(cat anvil/deployment.json | python3 -c "import sys, json; print(json.load(sys.stdin)['contract_address'])")
    print_success "Contract deployed at $CONTRACT_ADDRESS"
fi

# Update .env with contract address
print_step "Configuring environment..."
cat > backend/.env << EOF
DATABASE_URL=sqlite:///./agri_supply_chain.db
ANVIL_RPC_URL=http://127.0.0.1:8545
ANCHOR_CONTRACT_ADDRESS=$CONTRACT_ADDRESS
DEPLOYER_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
ANOMALY_THRESHOLD_LOW=30
ANOMALY_THRESHOLD_MEDIUM=70
ANOMALY_THRESHOLD_HIGH=70
ISOLATION_FOREST_CONTAMINATION=0.1
ISOLATION_FOREST_N_ESTIMATORS=100
ISOLATION_FOREST_RANDOM_STATE=42
BATCH_SIZE_FOR_ANCHORING=10
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
SECRET_KEY=dev-secret-key-change-in-production
EOF
print_success "Environment configured"

echo ""
echo "========================================="
echo "🎉 Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Start the backend server:"
echo "   cd backend && uvicorn app:app --reload --port 8000"
echo ""
echo "2. Access the application:"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Dashboard: http://localhost:8000/dashboard"
echo "   - Review UI: http://localhost:8000/reviews/ui"
echo "   - Traceability: http://localhost:8000/trace/TOS-2026-001/html"
echo ""
echo "3. Run the demo flow:"
echo "   - Submit events via API or UI"
echo "   - Review flagged events at /reviews/ui"
echo "   - Anchor batch: POST /anchor/batch/auto"
echo "   - Verify integrity: GET /trace/verify/{event_id}"
echo ""