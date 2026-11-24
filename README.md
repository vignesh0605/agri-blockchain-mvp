# Agri Supply Chain Blockchain MVP

A research-prototype MVP demonstrating **database-first storage** with **AI anomaly detection** and **blockchain anchoring** for agricultural supply chain traceability.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    LOCAL MVP ARCHITECTURE (DB-FIRST)                    │
├─────────────────────┬─────────────────────┬─────────────────────────────┤
│  Farmer / Edge UI   │   Anomaly Service   │   Database (SQLite)         │
│  (inputs data)      │   (FastAPI + ML)    │   — Primary storage         │
└───────┬─────────────┴───────┬─────────────┴──────────────┬────────────┘
        │                     │                            │
        │   1. Submit event   │                            │
        ▼                     ▼                            ▼
┌─────────────────┐  ┌───────────────────────┐  ┌─────────────────────┐
│   Validation    │→ │  AI Anomaly Score      │→ │  Store in SQLite    │
│   (schema check)│  │  (IsolationForest)     │  │  (status: pending)  │
└───────┬─────────┘  └───────┬───────────────┘  └──────────┬──────────┘
        │                     │                           │
        │   2. Flag if anomaly│                           │
        ▼                     ▼                           ▼
┌─────────────────┐  ┌───────────────────────┐  ┌─────────────────────┐
│   Manual Review │→ │  Review Queue (SQLite) │  │  status: flagged    │
│   (admin UI)    │  │  Score + raw data      │  │  or committed       │
└───────┬─────────┘  └───────┬───────────────┘  └──────────┬──────────┘
        │                     │                           │
        │   3. Accept & hash  │                           │
        ▼                     ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PERIODIC BATCH ANCHORING (cron / manual)             │
│  1. Query committed records from SQLite                                 │
│  2. Compute Merkle root / batch hash of new records                     │
│  3. Submit single transaction to Anvil: anchor(batchHash, timestamp)   │
│  4. Update SQLite: anchor_tx_hash, anchor_block_number                 │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Principle**: SQLite stores ALL data (prices, quality, GPS, timestamps, actors). Blockchain stores ONLY `keccak256(batch_json)` hashes — tiny, cheap, tamper-proof.

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Blockchain** | Foundry + Anvil (local Ethereum testnet) |
| **Smart Contracts** | Solidity (minimal hash anchoring only) |
| **AI Anomaly Detection** | scikit-learn IsolationForest + statsmodels SARIMA |
| **Backend API** | Python FastAPI |
| **Database** | SQLite (via SQLAlchemy) |
| **Admin UI** | FastAPI + Jinja2 templates |
| **Frontend** | HTMX + Tailwind CSS (via CDN) |

## Quick Start

### Prerequisites
- Python 3.11+
- Rust (for Foundry): `curl -L https://foundry.paradigm.xyz | bash && foundryup`

### 1. Clone & Setup
```bash
cd agri-blockchain-mvp
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python scripts/init_db.py
```

### 3. Start Anvil (Terminal 1)
```bash
cd anvil
./start.sh
```
Copy one of the private keys shown for deployment.

### 4. Deploy Anchor Contract (Terminal 2)
```bash
cd contracts
forge compile
forge create DataAnchor --rpc http://127.0.0.1:8545 \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
# Note the deployed contract address
```

### 5. Configure & Run Backend (Terminal 2)
```bash
cd backend
# Create .env with contract address:
cat > .env << EOF
DATABASE_URL=sqlite:///./agri_supply_chain.db
ANVIL_RPC_URL=http://127.0.0.1:8545
ANCHOR_CONTRACT_ADDRESS=0x...  # Your deployed contract address
DEPLOYER_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
EOF

uvicorn app:app --reload --port 8000
```

### 6. Access UI
- **API Docs**: http://localhost:8000/docs
- **Admin Dashboard**: http://localhost:8000/dashboard
- **Review Queue**: http://localhost:8000/reviews/ui
- **Traceability**: http://localhost:8000/trace/1/html

### 7. Generate Sample Data & Run Demo
```bash
# Generate sample data (farm, crop, events with anomalies)
python scripts/generate_sample_data.py

# Run full demo flow
bash scripts/demo_full_flow.sh
```

## Demo Scenario

**Scenario**: "Tomato Batch #TOM-2026-001 — Farm to Consumer with Anomaly Detection"

1. **Farmer registers**: Farm "Green Valley", wallet `0xf39Fd6e5...`
2. **Crop created**: 1000kg Tomatoes, variety "Roma", planted 2026-10-01
3. **Harvest event** (Dec 20): 950kg harvested, grade A, moisture 11% → score 12 → **committed**
4. **Processing event** (Dec 21): Washed, packed 20kg crates → score 8 → **committed**
5. **Logistics event** (Dec 22): Cold chain truck, 4°C, 200km → score 15 → **committed**
6. **Wholesale price** (Dec 23): ₹15/kg (normal market) → score 10 → **committed**
7. **Anomalous retail price** (Dec 25): Retailer enters ₹50/kg (vs ₹25 expected) → score **87** → **flagged**
8. **Admin review**: Sees price_change_pct +177%, volatility spike → **Accepts** (market surge) → committed
9. **Batch anchor**: 7 events → Merkle root `0xabc...` → anchored to Anvil block #42
10. **Consumer scans QR**: Sees full timeline + "Price anomaly detected & verified" badge
11. **Verification**: `GET /trace/verify/7` → shows on-chain anchor proves data unchanged since Dec 25

## Key Features

- **Database-First**: All rich data in SQLite (queryable, fast, local)
- **Minimal Blockchain**: Only 32-byte hashes on-chain — cheap, immutable proofs
- **AI Anomaly Detection**: Multi-variable (price, volume, quality, logistics, seasonality)
- **Human-in-the-Loop**: Admin reviews suspicious entries before permanent anchoring
- **End-to-End Traceability**: Consumer sees complete provenance with integrity proof
- **Local-First**: Runs entirely on a single machine for easy demo

## Project Structure

```
agri-blockchain-mvp/
├── anvil/                          # Anvil scripts
│   ├── start.sh
│   └── deploy_anchor.py
├── contracts/
│   └── DataAnchor.sol              # Minimal anchoring contract
├── backend/
│   ├── app.py                      # FastAPI app entry
│   ├── config.py                   # Settings
│   ├── database.py                 # SQLAlchemy models + session
│   ├── models.py                   # Pydantic schemas
│   ├── anomaly.py                  # IsolationForest detector
│   ├── sarima_detector.py          # SARIMA time-series
│   ├── anchor_service.py           # Batch anchoring to Anvil
│   ├── crud.py                     # Database operations
│   ├── routes/
│   │   ├── farms.py
│   │   ├── crops.py
│   │   ├── events.py
│   │   ├── reviews.py
│   │   ├── anchor.py
│   │   └── trace.py
│   └── templates/                  # Jinja2 templates
│       ├── base.html
│       ├── dashboard.html
│       ├── review_list.html
│       ├── review_detail.html
│       └── trace.html
├── scripts/
│   ├── init_db.py
│   ├── generate_sample_data.py
│   ├── demo_full_flow.sh
│   └── run_anchor_batch.py
├── tests/
│   ├── test_anomaly.py
│   ├── test_anchor.py
│   └── test_integration.py
├── .env.example
├── requirements.txt
├── foundry.toml
└── README.md
```

## API Endpoints

### Farms
- `POST /farms` - Create farm
- `GET /farms` - List farms
- `GET /farms/{id}` - Get farm

### Crops
- `POST /crops` - Create crop batch
- `GET /crops` - List crops
- `GET /crops/{id}` - Get crop
- `GET /crops/batch/{batch_code}` - Get by batch code

### Events
- `POST /events` - Submit supply chain event
- `GET /events` - List events (with filters)
- `GET /events/{id}` - Get event
- `GET /events/crop/{crop_id}` - Get crop timeline
- `GET /events/pending/review` - Flagged events
- `GET /events/committed/unanchored` - Events ready for anchoring
- `POST /events/{id}/commit` - Mark committed
- `POST /events/{id}/reject` - Reject event

### Reviews
- `GET /reviews` - List pending reviews
- `GET /reviews/{id}` - Get review
- `GET /reviews/event/{event_id}` - Get review for event
- `POST /reviews/{id}/action` - Accept/Reject/Request Info
- `GET /reviews/ui` - Admin review UI
- `GET /reviews/{id}/ui` - Review detail UI

### Anchoring
- `POST /anchor/batch` - Create batch anchor
- `POST /anchor/batch/submit` - Submit anchor to blockchain
- `POST /anchor/batch/auto` - Auto create & submit
- `GET /anchor` - List anchors
- `GET /anchor/latest` - Latest anchor
- `GET /anchor/verify/{event_id}` - Verify event integrity

### Traceability
- `GET /trace/{crop_id}` - Full traceability (JSON)
- `GET /trace/batch/{batch_code}` - Trace by batch code
- `GET /trace/{crop_id}/html` - Consumer traceability view
- `GET /trace/verify/{event_id}` - Verify data integrity

## Anomaly Detection

The system uses **Isolation Forest** (unsupervised, no training data needed) with these features:

| Feature | Description |
|---------|-------------|
| `price_change_pct` | % change from last price for same crop |
| `volume_zscore` | Standardized deviation from crop avg volume |
| `quality_index` | Composite score from grade, moisture |
| `lead_time_days` | Days from harvest to this event |
| `seasonal_factor` | Normalized month (1-12) |
| `volatility_7d` | 7-day rolling price std dev |
| `sarima_residual` | Residual from SARIMA price forecast |

**Thresholds**:
- ≤ 30: Normal → auto-committed
- 30-70: Suspicious → flagged for review
- > 70: Anomalous → high-priority review

Optional **SARIMA** (statsmodels) provides time-series residuals for price anomaly detection.

## Blockchain Anchoring

Only cryptographic hashes are stored on-chain:

1. **Event Hash**: `keccak256(canonical_json(event))`
2. **Merkle Tree**: Built from event hashes in batch
3. **Batch Hash**: `keccak256(merkle_root + prev_batch_hash + timestamp + count)`
4. **On-Chain**: Single `anchorBatch(batchHash, eventCount, prevBatchHash)` transaction

Verification proves data hasn't been tampered with since anchoring.

## Testing

```bash
# Unit tests
python -m pytest tests/test_anomaly.py -v
python -m pytest tests/test_anchor.py -v

# Integration tests
python -m pytest tests/test_integration.py -v
```

## Manual Verification Checklist

- [ ] Submit normal event → status=committed, no review created
- [ ] Submit anomalous price → status=flagged, review_queue entry created
- [ ] Admin accepts review → event.status=committed, review.status=accepted
- [ ] Admin rejects review → event.status=rejected, review.status=rejected
- [ ] Run anchor batch → transaction confirmed on Anvil, blockchain_anchors row created
- [ ] Verify event → returns on-chain anchor proof (tx_hash, block_number)
- [ ] Trace crop → shows complete timeline with anomaly flags
- [ ] Tamper test: modify SQLite data → verify detects mismatch vs on-chain hash

## Configuration

Key settings in `.env`:

```env
# Anomaly thresholds
ANOMALY_THRESHOLD_LOW=30
ANOMALY_THRESHOLD_MEDIUM=70
ANOMALY_THRESHOLD_HIGH=70

# Isolation Forest
ISOLATION_FOREST_CONTAMINATION=0.1
ISOLATION_FOREST_N_ESTIMATORS=100

# Batch anchoring
BATCH_SIZE_FOR_ANCHORING=10
```

## License

MIT License - Research prototype for demonstration purposes.

## References

- **Database-First Blockchain**: ProofLedger pattern, Merkle tree anchoring
- **AI Anomaly Detection**: scikit-learn IsolationForest, statsmodels SARIMA
- **Agri Standards**: FAO blockchain in agri-food, GS1 EPCIS, ISO 2382
- **Local Blockchain**: Foundry/Anvil documentation