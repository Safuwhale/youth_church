from fastapi import FastAPI
from routers import users, services, attendance, cells, health, tags
from fastapi.middleware.cors import CORSMiddleware
# --- CORS SETUP ---
# This tells FastAPI to trust requests coming from your React development server(frontend)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://church-frontend-delta.vercel.app",
    "https://horyc.vercel.app"
]

app = FastAPI(
    title="Attendance API",
    description="API backend for QR check-in system.",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(tags.router, prefix="/api/tags", tags=["Tags"])
app.include_router(services.router, prefix="/api/services", tags=["Services"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance (Scanner)"])
app.include_router(cells.router, prefix="/api/cells", tags=["Cell Groups"])
app.include_router(health.router, prefix="/api")

@app.get("/")
def read_root():
    return {"status": "online", "message": "Attendance API is running"}