from datetime import date

from sqlalchemy import func, select

from .db import SessionLocal, init_db
from .models import (
    Customer, CustomerPhone, Device, DeviceType, DiagnosticStep,
    Part, RepairJob, RepairPart, RepairTechnician, Supplier,
    SupplierPart, Technician
)

def seed_database():
    init_db()
    session = SessionLocal()
    try:
        count = session.scalar(select(func.count()).select_from(Customer)) or 0
        if count:
            return False

        console = DeviceType(type_name="Game Console", description="Home and handheld game systems")
        laptop = DeviceType(type_name="Laptop", description="Portable computers")
        phone = DeviceType(type_name="Phone", description="Smartphones")
        tablet = DeviceType(type_name="Tablet", description="Tablet computers")
        session.add_all([console, laptop, phone, tablet])
        session.flush()

        jane = Customer(
            first_name="Jane", last_name="Smith", email="jane@example.com",
            street="101 Main St", city="Rolla", state="MO", zip_code="65401"
        )
        alex = Customer(
            first_name="Alex", last_name="Brown", email="alex@example.com",
            street="25 Pine Rd", city="Rolla", state="MO", zip_code="65401"
        )
        sam = Customer(
            first_name="Sam", last_name="Lee", email="sam@example.com",
            street="88 Oak Ave", city="St. James", state="MO", zip_code="65559"
        )
        session.add_all([jane, alex, sam])
        session.flush()

        session.add_all([
            CustomerPhone(customer_id=jane.customer_id, phone_number="555-123-4567"),
            CustomerPhone(customer_id=alex.customer_id, phone_number="555-222-1000"),
            CustomerPhone(customer_id=sam.customer_id, phone_number="555-333-2000"),
        ])

        avery = Technician(
            first_name="Avery", last_name="Cole",
            email="avery@circuittrack.local", specialty="Game consoles"
        )
        morgan = Technician(
            first_name="Morgan", last_name="Diaz",
            email="morgan@circuittrack.local", specialty="Laptops and phones"
        )
        session.add_all([avery, morgan])
        session.flush()

        switch = Device(
            customer_id=jane.customer_id, device_type_id=console.device_type_id,
            brand="Nintendo", model="Switch Lite", serial_number="SWL-10001"
        )
        macbook = Device(
            customer_id=alex.customer_id, device_type_id=laptop.device_type_id,
            brand="Apple", model="MacBook Pro", serial_number="MBP-20002"
        )
        ps5 = Device(
            customer_id=sam.customer_id, device_type_id=console.device_type_id,
            brand="Sony", model="PlayStation 5", serial_number="PS5-30003"
        )
        session.add_all([switch, macbook, ps5])
        session.flush()

        repair1 = RepairJob(
            device_id=switch.device_id, date_received=date(2026, 9, 20),
            problem_description="Broken joystick and cracked screen",
            status="Diagnosing", labor_cost=25.00
        )
        repair2 = RepairJob(
            device_id=macbook.device_id, date_received=date(2026, 9, 18),
            problem_description="Does not charge reliably",
            status="Waiting for Parts", labor_cost=40.00
        )
        repair3 = RepairJob(
            device_id=ps5.device_id, date_received=date(2026, 9, 10),
            problem_description="Overheats after 20 minutes",
            status="Completed", completion_date=date(2026, 9, 15), labor_cost=60.00
        )
        session.add_all([repair1, repair2, repair3])
        session.flush()

        joystick = Part(
            part_name="Switch Joystick", description="Replacement analog stick",
            unit_cost=8.00, quantity_in_stock=8
        )
        usbc = Part(
            part_name="USB-C Port", description="Replacement charging port",
            unit_cost=4.50, quantity_in_stock=5
        )
        paste = Part(
            part_name="Thermal Paste", description="High performance thermal compound",
            unit_cost=7.50, quantity_in_stock=12
        )
        session.add_all([joystick, usbc, paste])
        session.flush()

        techparts = Supplier(
            supplier_name="TechParts Supply",
            email="sales@techparts.example", phone_number="555-700-1000"
        )
        components = Supplier(
            supplier_name="Repair Components",
            email="orders@repaircomponents.example", phone_number="555-700-2000"
        )
        session.add_all([techparts, components])
        session.flush()

        session.add_all([
            SupplierPart(supplier_id=techparts.supplier_id, part_id=joystick.part_id, supplier_price=7.25),
            SupplierPart(supplier_id=components.supplier_id, part_id=joystick.part_id, supplier_price=7.80),
            SupplierPart(supplier_id=techparts.supplier_id, part_id=usbc.part_id, supplier_price=4.00),
            SupplierPart(supplier_id=components.supplier_id, part_id=paste.part_id, supplier_price=6.90),
            RepairTechnician(repair_id=repair1.repair_id, technician_id=avery.technician_id, hours_worked=1.5),
            RepairTechnician(repair_id=repair2.repair_id, technician_id=morgan.technician_id, hours_worked=2.0),
            RepairTechnician(repair_id=repair3.repair_id, technician_id=avery.technician_id, hours_worked=2.5),
            DiagnosticStep(
                repair_id=repair1.repair_id, step_number=1, technician_id=avery.technician_id,
                description="Tested left joystick input",
                result="Left stick failed to register correctly",
                date_performed=date(2026, 9, 21)
            ),
            RepairPart(
                repair_id=repair1.repair_id, part_id=joystick.part_id,
                quantity_used=1, price_at_time_of_repair=8.00
            ),
        ])

        session.commit()
        return True
    finally:
        session.close()

if __name__ == "__main__":
    created = seed_database()
    print("Demo data created." if created else "Database already contains data. Seed skipped.")
