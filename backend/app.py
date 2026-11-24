"""Main FastAPI application entry point"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn

from config import settings
from database import init_db, get_db
from routes import farms, crops, events, reviews, anchor, trace
from anomaly import get_detector, train_detector
from models import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting Agri Supply Chain MVP...")
    init_db()

    # Train anomaly detector on existing data
    db = next(get_db())
    try:
        from database import SupplyChainEvent
        events = db.query(SupplyChainEvent).all()
        if events:
            event_dicts = []
            for e in events:
                event_dicts.append({
                    "id": e.id,
                    "crop_id": e.crop_id,
                    "event_type": e.event_type.value,
                    "actor_role": e.actor_role,
                    "actor_id": e.actor_id,
                    "timestamp": e.timestamp.timestamp() if e.timestamp else 0,
                    "location": e.location,
                    "data_json": e.data_json
                })
            train_detector(event_dicts)
            print(f"🤖 Anomaly detector trained on {len(event_dicts)} events")
    finally:
        db.close()

    print("✅ Startup complete")
    yield

    # Shutdown
    print("🛑 Shutting down...")


app = FastAPI(
    title="Agri Supply Chain Blockchain MVP",
    description="Database-first supply chain with AI anomaly detection and blockchain anchoring",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory="backend/templates")

# Include routers
app.include_router(farms.router)
app.include_router(crops.router)
app.include_router(events.router)
app.include_router(reviews.router)
app.include_router(anchor.router)
app.include_router(trace.router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Landing page"""
    return templates.TemplateResponse("base.html", {
        "request": request,
        "title": "Agri Supply Chain MVP"
    })


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    from database import engine
    from sqlalchemy import text

    # Check database
    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # Check blockchain
    bc_status = "not_configured"
    if settings.ANCHOR_CONTRACT_ADDRESS:
        from anchor_service import get_anchor_service
        service = get_anchor_service()
        if service.w3 and service.w3.is_connected():
            bc_status = "connected"
        else:
            bc_status = "disconnected"

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        database=db_status,
        blockchain=bc_status,
        timestamp=__import__("datetime").datetime.utcnow()
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Admin dashboard"""
    db = next(get_db())
    try:
        from database import SupplyChainEvent, EventStatus, ReviewQueue, ReviewStatus, AnomalyFlag, AnomalyStatus

        # Stats
        total_events = db.query(SupplyChainEvent).count()
        committed_events = db.query(SupplyChainEvent).filter(SupplyChainEvent.status == EventStatus.COMMITTED).count()
        flagged_events = db.query(SupplyChainEvent).filter(SupplyChainEvent.status == EventStatus.FLAGGED).count()
        pending_reviews = db.query(ReviewQueue).filter(ReviewQueue.status.in_([ReviewStatus.PENDING, ReviewStatus.IN_PROGRESS])).count()
        high_priority = db.query(ReviewQueue).join(AnomalyFlag).filter(
            AnomalyFlag.score >= 70,
            ReviewQueue.status.in_([ReviewStatus.PENDING, ReviewStatus.IN_PROGRESS])
        ).count()

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "total_events": total_events,
            "committed_events": committed_events,
            "flagged_events": flagged_events,
            "pending_reviews": pending_reviews,
            "high_priority": high_priority
        })
    finally:
        db.close()


@app.get("/reviews/ui", response_class=HTMLResponse)
async def reviews_ui(request: Request):
    """Admin review UI"""
    db = next(get_db())
    try:
        from crud import get_pending_reviews
        from database import SupplyChainEvent, AnomalyFlag

        reviews = get_pending_reviews(db)

        # Enrich with event and anomaly data
        review_data = []
        for review in reviews:
            event = db.query(SupplyChainEvent).filter(SupplyChainEvent.id == review.event_id).first()
            anomaly = db.query(AnomalyFlag).filter(AnomalyFlag.event_id == review.event_id).first()
            crop = event.crop if event else None
            farm = crop.farm if crop else None

            review_data.append({
                "review": review,
                "event": event,
                "anomaly": anomaly,
                "crop": crop,
                "farm": farm
            })

        return templates.TemplateResponse("review_list.html", {
            "request": request,
            "reviews": review_data
        })
    finally:
        db.close()


@app.get("/reviews/{review_id}/ui", response_class=HTMLResponse)
async def review_detail_ui(request: Request, review_id: int):
    """Review detail page"""
    db = next(get_db())
    try:
        from crud import get_review
        from database import SupplyChainEvent, AnomalyFlag

        review = get_review(db, review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        event = db.query(SupplyChainEvent).filter(SupplyChainEvent.id == review.event_id).first()
        anomaly = db.query(AnomalyFlag).filter(AnomalyFlag.event_id == review.event_id).first()
        crop = event.crop if event else None
        farm = crop.farm if crop else None

        # Get event history for context
        history = db.query(SupplyChainEvent).filter(
            SupplyChainEvent.crop_id == event.crop_id,
            SupplyChainEvent.id != event.id
        ).order_by(SupplyChainEvent.timestamp).all() if event else []

        return templates.TemplateResponse("review_detail.html", {
            "request": request,
            "review": review,
            "event": event,
            "anomaly": anomaly,
            "crop": crop,
            "farm": farm,
            "history": history
        })
    finally:
        db.close()


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    )