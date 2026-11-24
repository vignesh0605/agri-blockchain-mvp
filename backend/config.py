"""Configuration settings for the Agri Supply Chain MVP"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./agri_supply_chain.db"

    # Blockchain / Anvil
    ANVIL_RPC_URL: str = "http://127.0.0.1:8545"
    ANCHOR_CONTRACT_ADDRESS: Optional[str] = None  # Set after deployment
    DEPLOYER_PRIVATE_KEY: Optional[str] = None  # For deploying/anchoring

    # Anomaly Detection Thresholds
    ANOMALY_THRESHOLD_LOW: int = 30    # Normal
    ANOMALY_THRESHOLD_MEDIUM: int = 70 # Flagged for review
    ANOMALY_THRESHOLD_HIGH: int = 70   # High priority review

    # Isolation Forest params
    ISOLATION_FOREST_CONTAMINATION: float = 0.1
    ISOLATION_FOREST_N_ESTIMATORS: int = 100
    ISOLATION_FOREST_RANDOM_STATE: int = 42

    # Batch Anchoring
    BATCH_SIZE_FOR_ANCHORING: int = 10  # Events per batch

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()