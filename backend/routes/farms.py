"""Farm routes"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import FarmCreate, FarmUpdate, FarmResponse
from crud import (
    create_farm, get_farm, get_farm_by_gstin, get_farm_by_wallet,
    get_farms, update_farm, delete_farm
)

router = APIRouter(prefix="/farms", tags=["farms"])


@router.post("/", response_model=FarmResponse, status_code=status.HTTP_201_CREATED)
def create_farm_endpoint(farm: FarmCreate, db: Session = Depends(get_db)):
    """Create a new farm"""
    # Check for duplicate GSTIN
    if farm.gstin:
        existing = get_farm_by_gstin(db, farm.gstin)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Farm with GSTIN {farm.gstin} already exists"
            )
    # Check for duplicate wallet
    if farm.wallet_address:
        existing = get_farm_by_wallet(db, farm.wallet_address)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Farm with wallet {farm.wallet_address} already exists"
            )
    return create_farm(db, farm)


@router.get("/", response_model=List[FarmResponse])
def list_farms(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List all farms"""
    return get_farms(db, skip=skip, limit=limit)


@router.get("/{farm_id}", response_model=FarmResponse)
def get_farm_endpoint(farm_id: int, db: Session = Depends(get_db)):
    """Get a farm by ID"""
    farm = get_farm(db, farm_id)
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm with id {farm_id} not found"
        )
    return farm


@router.get("/gstin/{gstin}", response_model=FarmResponse)
def get_farm_by_gstin_endpoint(gstin: str, db: Session = Depends(get_db)):
    """Get a farm by GSTIN"""
    farm = get_farm_by_gstin(db, gstin)
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm with GSTIN {gstin} not found"
        )
    return farm


@router.get("/wallet/{wallet_address}", response_model=FarmResponse)
def get_farm_by_wallet_endpoint(wallet_address: str, db: Session = Depends(get_db)):
    """Get a farm by wallet address"""
    farm = get_farm_by_wallet(db, wallet_address)
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm with wallet {wallet_address} not found"
        )
    return farm


@router.patch("/{farm_id}", response_model=FarmResponse)
def update_farm_endpoint(farm_id: int, farm_update: FarmUpdate, db: Session = Depends(get_db)):
    """Update a farm"""
    farm = update_farm(db, farm_id, farm_update)
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm with id {farm_id} not found"
        )
    return farm


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm_endpoint(farm_id: int, db: Session = Depends(get_db)):
    """Delete a farm"""
    success = delete_farm(db, farm_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm with id {farm_id} not found"
        )