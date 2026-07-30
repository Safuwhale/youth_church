import os
import time
from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db

# Create a router (you can adjust the prefix to match your app structure)
router = APIRouter( tags=["System Health"])

# 1. Fetch the secret from Render's Environment Variables
# It defaults to a test string so it won't crash if you test locally before setting the env var.
CRON_SECRET = os.getenv("CRON_SECRET", "horyc-super-secret-cron-key")

@router.get("/health", status_code=status.HTTP_200_OK)
def system_health_check(
    # FastAPI automatically looks for a header named 'x-cron-secret'
    x_cron_secret: str = Header(None), 
    db: Session = Depends(get_db)
):
    """
    Secure System Health Check.
    Pings the Neon database to keep the connection pool warm and measures latency.
    Designed to be hit every 10-12 minutes by an external cron service.
    """
    # 2. The Security Bouncer
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Unauthorized access. Invalid or missing cron secret."
        )

    # 3. Base Health Status Template
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "disconnected",
        "db_latency_ms": 0,
    }
    
    try:
        # 4. Start the stopwatch
        start_time = time.time()
        
        # 5. Execute an ultra-lightweight query to test Neon DB
        db.execute(text("SELECT 1"))
        
        # 6. Stop the stopwatch and calculate milliseconds
        end_time = time.time()
        
        health_status["database"] = "connected"
        health_status["db_latency_ms"] = round((end_time - start_time) * 1000, 2)
        
    except Exception as e:
        # 7. Catch database sleep/connection errors securely
        health_status["status"] = "degraded"
        health_status["database"] = "error"
        health_status["error_details"] = str(e)
        
    return health_status