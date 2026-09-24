import os
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError

from .db import SessionLocal, init_db
from .models import (
    Customer, CustomerPhone, Device, DeviceType, DiagnosticStep,
    Part, RepairJob, RepairPart, RepairTechnician, Technician
)
from .seed import seed_database

app = FastAPI(title="CircuitTrack API", version="0.2.0")

# Local Vite development runs on 5173. Production serves the React build
# from FastAPI on the same origin, so CORS is not needed there.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_STATUSES = {"Received", "Diagnosing", "Waiting for Parts", "Repairing", "Completed"}

@app.on_event("startup")
def startup():
    init_db()
    if os.getenv("AUTO_SEED", "true").lower() in {"1", "true", "yes", "on"}:
        seed_database()

class CustomerCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    phone_numbers: list[str] = []

class DeviceCreate(BaseModel):
    customer_id: int
    device_type_id: int
    brand: str
    model: str
    serial_number: Optional[str] = None

class RepairCreate(BaseModel):
    device_id: int
    date_received: date = Field(default_factory=date.today)
    problem_description: str
    status: str = "Received"
    labor_cost: float = 0

class RepairStatusUpdate(BaseModel):
    status: str

class TechnicianAssignment(BaseModel):
    technician_id: int
    hours_worked: float = 0

class DiagnosticCreate(BaseModel):
    technician_id: int
    description: str
    result: Optional[str] = None
    date_performed: date = Field(default_factory=date.today)

class RepairPartCreate(BaseModel):
    part_id: int
    quantity_used: int = 1

class PartCreate(BaseModel):
    part_name: str
    description: Optional[str] = None
    unit_cost: float
    quantity_in_stock: int = 0

def mappings(session, sql, params=None):
    return [dict(row) for row in session.execute(text(sql), params or {}).mappings().all()]

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/dashboard")
def dashboard():
    session = SessionLocal()
    try:
        counts = {
            "customers": session.scalar(select(func.count()).select_from(Customer)) or 0,
            "devices": session.scalar(select(func.count()).select_from(Device)) or 0,
            "active_repairs": session.scalar(
                select(func.count()).select_from(RepairJob).where(RepairJob.status != "Completed")
            ) or 0,
            "waiting_for_parts": session.scalar(
                select(func.count()).select_from(RepairJob).where(RepairJob.status == "Waiting for Parts")
            ) or 0,
            "completed_repairs": session.scalar(
                select(func.count()).select_from(RepairJob).where(RepairJob.status == "Completed")
            ) or 0,
        }

        recent = mappings(session, """
            SELECT r.repair_id, r.date_received, r.status,
                   c.first_name || ' ' || c.last_name AS customer_name,
                   d.brand || ' ' || d.model AS device_name
            FROM repair_job r
            JOIN device d ON d.device_id = r.device_id
            JOIN customer c ON c.customer_id = d.customer_id
            ORDER BY r.repair_id DESC
            LIMIT 8
        """)

        stats = session.execute(text("""
            SELECT COUNT(*) AS completed_count,
                   ROUND(CAST(AVG(total_cost) AS numeric), 2) AS avg_cost,
                   ROUND(CAST(MIN(total_cost) AS numeric), 2) AS min_cost,
                   ROUND(CAST(MAX(total_cost) AS numeric), 2) AS max_cost
            FROM (
                SELECT r.repair_id,
                       r.labor_cost + COALESCE(SUM(
                           rp.quantity_used * rp.price_at_time_of_repair
                       ), 0) AS total_cost
                FROM repair_job r
                LEFT JOIN repair_part rp ON rp.repair_id = r.repair_id
                WHERE r.status = 'Completed'
                GROUP BY r.repair_id, r.labor_cost
            ) totals
        """)).mappings().first()

        # SQLite does not support CAST(... AS numeric) the same way for ROUND in all builds.
        # If the portable aggregate query above fails in a future SQLite version, the rest
        # of the application is unaffected. Current SQLite/Postgres both handle it.
        return {
            "counts": counts,
            "recent_repairs": recent,
            "completed_cost_stats": dict(stats) if stats else {},
        }
    finally:
        session.close()

@app.get("/api/device-types")
def list_device_types():
    session = SessionLocal()
    try:
        return mappings(session, "SELECT * FROM device_type ORDER BY type_name")
    finally:
        session.close()

@app.get("/api/customers")
def list_customers(q: Optional[str] = None):
    session = SessionLocal()
    try:
        if q:
            return mappings(session, """
                SELECT * FROM customer
                WHERE lower(first_name) LIKE lower(:q)
                   OR lower(last_name) LIKE lower(:q)
                   OR lower(COALESCE(email,'')) LIKE lower(:q)
                ORDER BY last_name, first_name
            """, {"q": f"%{q}%"})
        return mappings(session, "SELECT * FROM customer ORDER BY last_name, first_name")
    finally:
        session.close()

@app.post("/api/customers", status_code=201)
def create_customer(data: CustomerCreate):
    session = SessionLocal()
    try:
        customer = Customer(
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            email=data.email,
            city=data.city,
            state=data.state.upper() if data.state else None,
        )
        session.add(customer)
        session.flush()
        for phone in data.phone_numbers:
            if phone.strip():
                session.add(CustomerPhone(
                    customer_id=customer.customer_id,
                    phone_number=phone.strip()
                ))
        session.commit()
        return {"customer_id": customer.customer_id}
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(400, "Customer data violates a database constraint.") from exc
    finally:
        session.close()

@app.get("/api/customers/{customer_id}/history")
def customer_history(customer_id: int):
    session = SessionLocal()
    try:
        customer = session.get(Customer, customer_id)
        if not customer:
            raise HTTPException(404, "Customer not found")

        history = mappings(session, """
            SELECT d.device_id, dt.type_name, d.brand, d.model, d.serial_number,
                   r.repair_id, r.date_received, r.status,
                   r.problem_description, r.completion_date
            FROM device d
            JOIN device_type dt ON dt.device_type_id = d.device_type_id
            LEFT JOIN repair_job r ON r.device_id = d.device_id
            WHERE d.customer_id = :customer_id
            ORDER BY d.device_id, r.date_received DESC
        """, {"customer_id": customer_id})

        return {
            "customer": {
                "customer_id": customer.customer_id,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "email": customer.email,
                "city": customer.city,
                "state": customer.state,
            },
            "history": history,
        }
    finally:
        session.close()

@app.get("/api/devices")
def list_devices():
    session = SessionLocal()
    try:
        return mappings(session, """
            SELECT d.*, c.first_name || ' ' || c.last_name AS customer_name,
                   dt.type_name
            FROM device d
            JOIN customer c ON c.customer_id = d.customer_id
            JOIN device_type dt ON dt.device_type_id = d.device_type_id
            ORDER BY d.device_id DESC
        """)
    finally:
        session.close()

@app.post("/api/devices", status_code=201)
def create_device(data: DeviceCreate):
    session = SessionLocal()
    try:
        if not session.get(Customer, data.customer_id):
            raise HTTPException(400, "Customer does not exist")
        if not session.get(DeviceType, data.device_type_id):
            raise HTTPException(400, "Device type does not exist")

        device = Device(
            customer_id=data.customer_id,
            device_type_id=data.device_type_id,
            brand=data.brand.strip(),
            model=data.model.strip(),
            serial_number=data.serial_number or None,
        )
        session.add(device)
        session.commit()
        session.refresh(device)
        return {"device_id": device.device_id}
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(400, "Serial number must be unique.") from exc
    finally:
        session.close()

@app.get("/api/technicians")
def list_technicians():
    session = SessionLocal()
    try:
        return mappings(session, "SELECT * FROM technician ORDER BY last_name, first_name")
    finally:
        session.close()

@app.get("/api/parts")
def list_parts():
    session = SessionLocal()
    try:
        return mappings(session, "SELECT * FROM part ORDER BY part_name")
    finally:
        session.close()

@app.post("/api/parts", status_code=201)
def create_part(data: PartCreate):
    if data.unit_cost < 0 or data.quantity_in_stock < 0:
        raise HTTPException(400, "Cost and inventory cannot be negative")
    session = SessionLocal()
    try:
        part = Part(
            part_name=data.part_name.strip(),
            description=data.description,
            unit_cost=data.unit_cost,
            quantity_in_stock=data.quantity_in_stock,
        )
        session.add(part)
        session.commit()
        session.refresh(part)
        return {"part_id": part.part_id}
    finally:
        session.close()

@app.delete("/api/parts/{part_id}")
def delete_part(part_id: int):
    session = SessionLocal()
    try:
        part = session.get(Part, part_id)
        if not part:
            raise HTTPException(404, "Part not found")
        used = session.scalar(
            select(func.count()).select_from(RepairPart).where(RepairPart.part_id == part_id)
        ) or 0
        if used:
            raise HTTPException(
                409, "Part is referenced by repair history and cannot be deleted."
            )
        session.delete(part)
        session.commit()
        return {"deleted": True}
    finally:
        session.close()

@app.get("/api/repairs")
def list_repairs(status: Optional[str] = None):
    session = SessionLocal()
    try:
        sql = """
            SELECT r.*,
                   c.first_name || ' ' || c.last_name AS customer_name,
                   d.brand || ' ' || d.model AS device_name
            FROM repair_job r
            JOIN device d ON d.device_id = r.device_id
            JOIN customer c ON c.customer_id = d.customer_id
        """
        params = {}
        if status:
            sql += " WHERE r.status = :status"
            params["status"] = status
        sql += " ORDER BY r.repair_id DESC"
        return mappings(session, sql, params)
    finally:
        session.close()

@app.post("/api/repairs", status_code=201)
def create_repair(data: RepairCreate):
    if data.status not in VALID_STATUSES:
        raise HTTPException(400, "Invalid repair status")
    if data.labor_cost < 0:
        raise HTTPException(400, "Labor cost cannot be negative")

    session = SessionLocal()
    try:
        if not session.get(Device, data.device_id):
            raise HTTPException(400, "Device does not exist")
        repair = RepairJob(
            device_id=data.device_id,
            date_received=data.date_received,
            problem_description=data.problem_description.strip(),
            status=data.status,
            labor_cost=data.labor_cost,
        )
        session.add(repair)
        session.commit()
        session.refresh(repair)
        return {"repair_id": repair.repair_id}
    finally:
        session.close()

@app.patch("/api/repairs/{repair_id}/status")
def update_repair_status(repair_id: int, data: RepairStatusUpdate):
    if data.status not in VALID_STATUSES:
        raise HTTPException(400, "Invalid repair status")

    session = SessionLocal()
    try:
        repair = session.get(RepairJob, repair_id)
        if not repair:
            raise HTTPException(404, "Repair not found")
        repair.status = data.status
        repair.completion_date = date.today() if data.status == "Completed" else None
        session.commit()
        return {"updated": True}
    finally:
        session.close()

@app.post("/api/repairs/{repair_id}/technicians")
def assign_technician(repair_id: int, data: TechnicianAssignment):
    if data.hours_worked < 0:
        raise HTTPException(400, "Hours worked cannot be negative")

    session = SessionLocal()
    try:
        if not session.get(RepairJob, repair_id):
            raise HTTPException(404, "Repair not found")
        if not session.get(Technician, data.technician_id):
            raise HTTPException(400, "Technician not found")

        row = session.get(RepairTechnician, (repair_id, data.technician_id))
        if row:
            row.hours_worked = data.hours_worked
        else:
            session.add(RepairTechnician(
                repair_id=repair_id,
                technician_id=data.technician_id,
                hours_worked=data.hours_worked,
            ))
        session.commit()
        return {"saved": True}
    finally:
        session.close()

@app.post("/api/repairs/{repair_id}/diagnostics")
def add_diagnostic(repair_id: int, data: DiagnosticCreate):
    session = SessionLocal()
    try:
        if not session.get(RepairJob, repair_id):
            raise HTTPException(404, "Repair not found")
        if not session.get(Technician, data.technician_id):
            raise HTTPException(400, "Technician not found")

        next_step = session.scalar(
            select(func.coalesce(func.max(DiagnosticStep.step_number), 0) + 1)
            .where(DiagnosticStep.repair_id == repair_id)
        )

        session.add(DiagnosticStep(
            repair_id=repair_id,
            step_number=int(next_step),
            technician_id=data.technician_id,
            description=data.description.strip(),
            result=data.result,
            date_performed=data.date_performed,
        ))
        session.commit()
        return {"step_number": int(next_step)}
    finally:
        session.close()

@app.post("/api/repairs/{repair_id}/parts")
def add_part_to_repair(repair_id: int, data: RepairPartCreate):
    if data.quantity_used <= 0:
        raise HTTPException(400, "Quantity must be positive")

    session = SessionLocal()
    try:
        repair = session.get(RepairJob, repair_id)
        part = session.get(Part, data.part_id)
        if not repair:
            raise HTTPException(404, "Repair not found")
        if not part:
            raise HTTPException(404, "Part not found")
        if part.quantity_in_stock < data.quantity_used:
            raise HTTPException(409, "Not enough inventory")

        row = session.get(RepairPart, (repair_id, data.part_id))
        if row:
            row.quantity_used += data.quantity_used
        else:
            session.add(RepairPart(
                repair_id=repair_id,
                part_id=data.part_id,
                quantity_used=data.quantity_used,
                price_at_time_of_repair=part.unit_cost,
            ))

        part.quantity_in_stock -= data.quantity_used
        session.commit()
        return {"saved": True}
    finally:
        session.close()

@app.get("/api/repairs/{repair_id}")
def repair_details(repair_id: int):
    session = SessionLocal()
    try:
        repair = session.execute(text("""
            SELECT r.*, d.brand, d.model, d.serial_number,
                   c.customer_id,
                   c.first_name || ' ' || c.last_name AS customer_name
            FROM repair_job r
            JOIN device d ON d.device_id = r.device_id
            JOIN customer c ON c.customer_id = d.customer_id
            WHERE r.repair_id = :repair_id
        """), {"repair_id": repair_id}).mappings().first()

        if not repair:
            raise HTTPException(404, "Repair not found")

        technicians = mappings(session, """
            SELECT t.technician_id,
                   t.first_name || ' ' || t.last_name AS technician_name,
                   rt.hours_worked
            FROM repair_technician rt
            JOIN technician t ON t.technician_id = rt.technician_id
            WHERE rt.repair_id = :repair_id
        """, {"repair_id": repair_id})

        diagnostics = mappings(session, """
            SELECT ds.*,
                   t.first_name || ' ' || t.last_name AS technician_name
            FROM diagnostic_step ds
            JOIN technician t ON t.technician_id = ds.technician_id
            WHERE ds.repair_id = :repair_id
            ORDER BY ds.step_number
        """, {"repair_id": repair_id})

        parts = mappings(session, """
            SELECT p.part_name, rp.part_id, rp.quantity_used,
                   rp.price_at_time_of_repair,
                   ROUND(CAST(
                       rp.quantity_used * rp.price_at_time_of_repair AS numeric
                   ), 2) AS line_total
            FROM repair_part rp
            JOIN part p ON p.part_id = rp.part_id
            WHERE rp.repair_id = :repair_id
        """, {"repair_id": repair_id})

        parts_total = sum(float(p["line_total"]) for p in parts)
        total_cost = float(repair["labor_cost"]) + parts_total

        return {
            "repair": dict(repair),
            "technicians": technicians,
            "diagnostics": diagnostics,
            "parts": parts,
            "parts_total": round(parts_total, 2),
            "total_cost": round(total_cost, 2),
        }
    finally:
        session.close()

# In production Docker builds the React frontend into /app/frontend_dist.
# Mount it last so /api/* routes continue to take precedence.
frontend_dist = Path(__file__).resolve().parents[1] / "frontend_dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
