from fastapi import FastAPI
from database import engine, Base
from routers import users
import models # Imports models so SQLAlchemy knows to create the tables

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Youth Church Attendance API",
    description="API backend for the Flipped QR check-in system.",
    version="1.0.0"
)

app.include_router(users.router, prefix="/api/users", tags=["Users"])

@app.get("/")
def read_root():
    return {"status": "online", "message": "Youth Church API is running"}