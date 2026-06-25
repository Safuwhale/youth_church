from fastapi import FastAPI
from database import engine, Base
from routers import users, services, attendance, cells
import models

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Youth Church Attendance API",
    description="API backend for the Two way QR check-in system.",
    version="1.0.0"
)

app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(services.router, prefix="/api/services", tags=["Services"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance (Scanner)"])
app.include_router(cells.router, prefix="/api/cells", tags=["Cell Groups"])

@app.get("/")
def read_root():
    return {"status": "online", "message": "Youth Church API is running"}