from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    permissions = Column(String) # JSON or simple string

    devices = relationship("Device", back_populates="user")
    floor_plans = relationship("FloorPlan", back_populates="user")

class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mac_address = Column(String, unique=True, index=True)
    device_name = Column(String)
    device_type = Column(String)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))

    user = relationship("User", back_populates="devices")
    signal_readings = relationship("SignalReading", back_populates="device", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="device", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="device", cascade="all, delete-orphan")

class AccessPoint(Base):
    __tablename__ = "access_points"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mac_address = Column(String, unique=True)
    name = Column(String)
    floor_id = Column(UUID(as_uuid=True), ForeignKey('floor_plans.id'))
    position_x = Column(Float)
    position_y = Column(Float)
    calibration_offset = Column(Float, default=-40.0)
    signal_strength = Column(Float)
    last_seen = Column(DateTime)

    floor_plan = relationship("FloorPlan", back_populates="access_points")
    signal_readings = relationship("SignalReading", back_populates="access_point")
    calibration_data = relationship("CalibrationData", back_populates="access_point")

class SignalReading(Base):
    __tablename__ = "signal_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.id'), index=True)
    access_point_id = Column(UUID(as_uuid=True), ForeignKey('access_points.id'))
    raw_rssi = Column(Float)
    filtered_rssi = Column(Float)
    channel = Column(Integer)
    frequency = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    device = relationship("Device", back_populates="signal_readings")
    access_point = relationship("AccessPoint", back_populates="signal_readings")

    __table_args__ = (
        Index('idx_sig_device_time', 'device_id', 'timestamp'),
    )

class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.id'), index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey('zones.id'), nullable=True)
    x = Column(Float)
    y = Column(Float)
    z = Column(Float, default=0.0)
    confidence_score = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    device = relationship("Device", back_populates="positions")
    zone = relationship("Zone", back_populates="positions")

    __table_args__ = (
        Index('idx_pos_device_time', 'device_id', 'timestamp'),
    )

class Zone(Base):
    __tablename__ = "zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    zone_type = Column(String)
    floor_id = Column(UUID(as_uuid=True), ForeignKey('floor_plans.id'))
    x_min = Column(Float)
    y_min = Column(Float)
    x_max = Column(Float)
    y_max = Column(Float)
    color = Column(String)
    parent_zone_id = Column(UUID(as_uuid=True), ForeignKey('zones.id'), nullable=True)

    floor_plan = relationship("FloorPlan", back_populates="zones")
    positions = relationship("Position", back_populates="zone")
    activity_logs = relationship("ActivityLog", back_populates="zone")

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.id'))
    zone_id = Column(UUID(as_uuid=True), ForeignKey('zones.id'))
    activity_type = Column(String) # entered, exited, stationary, moving
    timestamp = Column(DateTime, default=datetime.utcnow)
    duration_seconds = Column(Float, nullable=True)

    device = relationship("Device", back_populates="activity_logs")
    zone = relationship("Zone", back_populates="activity_logs")

class CalibrationData(Base):
    __tablename__ = "calibration_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    access_point_id = Column(UUID(as_uuid=True), ForeignKey('access_points.id'))
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.id'))
    actual_distance_meters = Column(Float)
    measured_rssi = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

    access_point = relationship("AccessPoint", back_populates="calibration_data")

class FloorPlan(Base):
    __tablename__ = "floor_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    name = Column(String)
    width = Column(Float)
    height = Column(Float)
    unit = Column(String, default="meters")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="floor_plans")
    zones = relationship("Zone", back_populates="floor_plan", cascade="all, delete-orphan")
    access_points = relationship("AccessPoint", back_populates="floor_plan", cascade="all, delete-orphan")
