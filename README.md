# Youth Church Attendance API (Two-Way QR System)

A high-performance, robust REST API built to handle Sunday service check-ins via a "Two-Way QR" architecture. Ushers can use their devices to scan the youths' unique QR IDs, or youths can scan a service Qr-poster, eliminating door bottlenecks and preventing "ghost attendance."

---

## Features

- **Role-Based Access Control (RBAC):** Distinct permissions for Members, Ushers, Cell Leaders, and the HOD.
- **JWT Authentication:** Secure stateless sessions using PyJWT and bcrypt password hashing.
- **Service Gatekeeper:** Sunday services can be activated/deactivated to control check-in windows.
- **Bi-Directional Scanning:** Supports both Usher-led QR scanning and Self-Service poster scanning.
- **Cell Group Analytics:** Real-time cross-referencing to generate cell-specific absentee lists.
- **Automated Export:** Generates raw `.csv` data exports for HOD administrative reporting.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (Python) |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Security | bcrypt, PyJWT |

---

## Local Setup Instructions

### 1. Clone & Environment

Clone the repository and set up a Python virtual environment:

```bash
git clone https://github.com/Safuwhale/youth_church.git
cd youth_church
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Database Configuration

Ensure PostgreSQL is running on your machine. Update the connection string inside `database.py` with your local PostgreSQL credentials:

```python
SQLALCHEMY_DATABASE_URL = "postgresql://username:password@localhost/youth_church"
```

### 4. Initialize Database & Seed Admin(for test)

The tables will automatically generate on startup. To create the master HOD account, run the seed script:

```bash
python seed_admin.py
```

> This creates an HOD user with **Phone:** `08000000000` and **Password:** `admin123`.

### 5. Run the Server

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

---

## API Documentation

This API adheres to the OpenAPI standard. Once the server is running locally, you can view the documentation in two formats:

- **Interactive Testing (Swagger):** http://127.0.0.1:8000/docs
- **Api Documentation- API Reference (ReDoc):** http://127.0.0.1:8000/redoc
- **Raw OpenAPI Schema:** http://127.0.0.1:8000/openapi.json

---

## Core Endpoint Map

| Feature | Endpoint | Method | Role Required |
|---------|----------|--------|---------------|
| Auth | `/api/users/login` | POST | Public |
| Auth | `/api/users/onboard` | POST | Public |
| Profile | `/api/users/me` | GET | Member+ |
| Search | `/api/users/search` | GET | Usher+ |
| Gates | `/api/services/create` | POST | HOD |
| Gates | `/api/services/{id}/activate` | PATCH | HOD |
| Scan | `/api/attendance/scan` | POST | Usher+ |
| Scan | `/api/attendance/self-checkin` | POST | Member+ |
| Export | `/api/attendance/export` | GET | HOD |
| Cells | `/api/cells/my-cell` | GET | Leader |