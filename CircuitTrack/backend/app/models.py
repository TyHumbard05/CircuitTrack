from sqlalchemy import (
    CheckConstraint, Column, Date, Float, ForeignKey, Integer,
    String, Text, UniqueConstraint
)
from .db import Base

class Customer(Base):
    __tablename__ = "customer"
    customer_id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100))
    street = Column(String(100))
    city = Column(String(50))
    state = Column(String(2))
    zip_code = Column(String(10))
    __table_args__ = (
        CheckConstraint("state IS NULL OR length(state) = 2", name="ck_customer_state_len"),
    )

class CustomerPhone(Base):
    __tablename__ = "customer_phone"
    customer_id = Column(
        Integer, ForeignKey("customer.customer_id", ondelete="CASCADE"), primary_key=True
    )
    phone_number = Column(String(20), primary_key=True)

class DeviceType(Base):
    __tablename__ = "device_type"
    device_type_id = Column(Integer, primary_key=True, autoincrement=True)
    type_name = Column(String(50), nullable=False, unique=True)
    description = Column(String(255))

class Device(Base):
    __tablename__ = "device"
    device_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(
        Integer, ForeignKey("customer.customer_id", ondelete="RESTRICT"), nullable=False
    )
    device_type_id = Column(
        Integer, ForeignKey("device_type.device_type_id", ondelete="RESTRICT"), nullable=False
    )
    brand = Column(String(50), nullable=False)
    model = Column(String(80), nullable=False)
    serial_number = Column(String(100), unique=True)

class Technician(Base):
    __tablename__ = "technician"
    technician_id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    specialty = Column(String(100))

class RepairJob(Base):
    __tablename__ = "repair_job"
    repair_id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(
        Integer, ForeignKey("device.device_id", ondelete="RESTRICT"), nullable=False
    )
    date_received = Column(Date, nullable=False)
    problem_description = Column(Text, nullable=False)
    status = Column(String(30), nullable=False)
    completion_date = Column(Date)
    labor_cost = Column(Float, nullable=False, default=0)
    __table_args__ = (
        CheckConstraint(
            "status IN ('Received','Diagnosing','Waiting for Parts','Repairing','Completed')",
            name="ck_repair_status",
        ),
        CheckConstraint("labor_cost >= 0", name="ck_repair_labor_nonnegative"),
        CheckConstraint(
            "completion_date IS NULL OR completion_date >= date_received",
            name="ck_repair_completion_date",
        ),
    )

class Part(Base):
    __tablename__ = "part"
    part_id = Column(Integer, primary_key=True, autoincrement=True)
    part_name = Column(String(100), nullable=False)
    description = Column(String(255))
    unit_cost = Column(Float, nullable=False)
    quantity_in_stock = Column(Integer, nullable=False, default=0)
    __table_args__ = (
        CheckConstraint("unit_cost >= 0", name="ck_part_cost_nonnegative"),
        CheckConstraint("quantity_in_stock >= 0", name="ck_part_stock_nonnegative"),
    )

class Supplier(Base):
    __tablename__ = "supplier"
    supplier_id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_name = Column(String(100), nullable=False)
    email = Column(String(100))
    phone_number = Column(String(20))

class DiagnosticStep(Base):
    __tablename__ = "diagnostic_step"
    repair_id = Column(
        Integer, ForeignKey("repair_job.repair_id", ondelete="CASCADE"), primary_key=True
    )
    step_number = Column(Integer, primary_key=True)
    technician_id = Column(
        Integer, ForeignKey("technician.technician_id", ondelete="RESTRICT"), nullable=False
    )
    description = Column(Text, nullable=False)
    result = Column(Text)
    date_performed = Column(Date, nullable=False)
    __table_args__ = (
        CheckConstraint("step_number > 0", name="ck_diagnostic_step_positive"),
    )

class RepairTechnician(Base):
    __tablename__ = "repair_technician"
    repair_id = Column(
        Integer, ForeignKey("repair_job.repair_id", ondelete="CASCADE"), primary_key=True
    )
    technician_id = Column(
        Integer, ForeignKey("technician.technician_id", ondelete="RESTRICT"), primary_key=True
    )
    hours_worked = Column(Float, nullable=False, default=0)
    __table_args__ = (
        CheckConstraint("hours_worked >= 0", name="ck_hours_nonnegative"),
    )

class RepairPart(Base):
    __tablename__ = "repair_part"
    repair_id = Column(
        Integer, ForeignKey("repair_job.repair_id", ondelete="CASCADE"), primary_key=True
    )
    part_id = Column(
        Integer, ForeignKey("part.part_id", ondelete="RESTRICT"), primary_key=True
    )
    quantity_used = Column(Integer, nullable=False)
    price_at_time_of_repair = Column(Float, nullable=False)
    __table_args__ = (
        CheckConstraint("quantity_used > 0", name="ck_repair_part_qty_positive"),
        CheckConstraint(
            "price_at_time_of_repair >= 0", name="ck_repair_part_price_nonnegative"
        ),
    )

class SupplierPart(Base):
    __tablename__ = "supplier_part"
    supplier_id = Column(
        Integer, ForeignKey("supplier.supplier_id", ondelete="CASCADE"), primary_key=True
    )
    part_id = Column(
        Integer, ForeignKey("part.part_id", ondelete="CASCADE"), primary_key=True
    )
    supplier_price = Column(Float, nullable=False)
    __table_args__ = (
        CheckConstraint("supplier_price >= 0", name="ck_supplier_price_nonnegative"),
    )
