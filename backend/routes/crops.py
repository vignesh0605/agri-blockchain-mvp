"""Crop routes"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import CropCreate, CropUpdate, CropResponse
from crud import (
    create_crop, get_crop, get_crop_by_batch_code,
    get_crops, update_crop, delete_crop
)

router = APIRouter(prefix="/crops", tags=["crops"])


@router.post("/", response_model=CropResponse, status_code=status.HTTP_201_CREATED)
def create_crop_endpoint(crop: CropCreate, db: Session = Depends(get_db)):
    """Create a new crop batch"""
    # Check for duplicate batch code
    existing = get_crop_by_batch_code(db, crop.batch_code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Crop with batch code {crop.batch_code} already exists"
        )
    return create_crop(db, crop)


@router.get("/", response_model=List[CropResponse])
def list_crops(
    farm_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List all crops, optionally filtered by farm"""
    return get_crops(db, farm_id=farm_id, skip=skip, limit=limit)


@router.get("/{crop_id}", response_model=CropResponse)
def get_crop_endpoint(crop_id: int, db: Session = Depends(get_db)):
    """Get a crop by ID"""
    crop = get_crop(db, crop_id)
    if not crop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crop with id {crop_id} not found"
        )
    return crop


@router.get("/batch/{batch_code}", response_model=CropResponse)
def get_crop_by_batch_code_endpoint(batch_code: str, db: Session = Depends(get_db)):
    """Get a crop by batch code"""
    crop = get_crop_by_batch_code(db, batch_code)
    if not crop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crop with batch code {batch_code} not found"
        )
    return crop


@router.patch("/{crop_id}", response_model=CropResponse)
def update_crop_endpoint(crop_id: int, crop_update: CropUpdate, db: Session = Depends(get_db)):
    """Update a crop"""
    crop = update_crop(db, crop_id, crop_update)
    if not crop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crop with id {crop_id} not found"
        )
    return crop


@router.delete("/{crop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_crop_endpoint(crop_id: int, db: Session = Depends(get_db)):
    """Delete a crop"""
    success = delete_crop(db, crop_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crop with id {crop_id} not found"
        )