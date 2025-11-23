from typing import Optional
import datetime
import decimal
import os

from sqlalchemy import (
    CheckConstraint, DECIMAL, Date, Enum, ForeignKeyConstraint,
    Index, Integer, JSON, String, Text, Time, text, create_engine
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from dotenv import load_dotenv

import uuid

from sqlalchemy import (
    create_engine, Integer, String, DateTime, ForeignKey, Enum, Index
)
from sqlalchemy.sql import func

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("DATABASE_URL is missing! Check your .env file.")

# ENGINE CONFIG
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ============ MODELS ============

# TimetableVersion and TimetableEntry (DB-agnostic, consistent with Integer PKs elsewhere)

class TimetableVersion(Base):
    __tablename__ = "timetable_versions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    name: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), server_default="draft")

    # DB side timestamp → NO deprecation warnings
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    entries: Mapped[list["TimetableEntry"]] = relationship(
        "TimetableEntry", back_populates="version", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_timetable_versions_created_at", "created_at"),
    )


# TimetableEntry
class TimetableEntry(Base):
    __tablename__ = "timetable_entries"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("timetable_versions.id", ondelete="CASCADE"),
        nullable=False
    )

    # These IDs MUST match the PK type of your main models → INTEGER
    subject_offering_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("subject_offerings.id", ondelete="SET NULL")
    )
    faculty_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("faculty.id", ondelete="SET NULL")
    )
    batch_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("batches.id", ondelete="SET NULL")
    )
    room_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("rooms.id", ondelete="SET NULL")
    )

    day: Mapped[int] = mapped_column(Integer, nullable=False)
    slot: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    version: Mapped["TimetableVersion"] = relationship("TimetableVersion", back_populates="entries")
    subject_offering: Mapped[Optional["SubjectOfferings"]] = relationship("SubjectOfferings")
    faculty: Mapped[Optional["Faculty"]] = relationship("Faculty")
    batch: Mapped[Optional["Batches"]] = relationship("Batches")
    room: Mapped[Optional["Rooms"]] = relationship("Rooms")

    __table_args__ = (
        Index("idx_tt_entries_version", "version_id"),
        Index("idx_tt_entries_batch_day_slot", "batch_id", "day", "slot"),
        Index("idx_tt_entries_faculty_day_slot", "faculty_id", "day", "slot"),
    )

class Config(Base):
    __tablename__ = 'config'

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text)


class Departments(Base):
    __tablename__ = 'departments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    batches = relationship("Batches", back_populates="department")
    faculty = relationship("Faculty", back_populates="department")
    subjects = relationship("Subjects", back_populates="department")


class Rooms(Base):
    __tablename__ = 'rooms'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(Enum("theory", "lab", name="room_type"))
    location: Mapped[Optional[str]] = mapped_column(String(128))

    fixed_slots = relationship("FixedSlots", back_populates="room")


class Timeslots(Base):
    __tablename__ = 'timeslots'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[int] = mapped_column(Integer, nullable=False)
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    end_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)

    __table_args__ = (
        Index("unique_day_slot", "day", "slot", unique=True),
    )


class Batches(Base):
    __tablename__ = 'batches'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(Integer)
    shift: Mapped[str] = mapped_column(
        Enum("day", "evening", name="shift_enum"),
        server_default="day"
    )

    department = relationship("Departments", back_populates="batches")
    subject_offerings = relationship("SubjectOfferings", back_populates="batch")


class Faculty(Base):
    __tablename__ = 'faculty'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(150), unique=True)
    department_id: Mapped[Optional[int]] = mapped_column(Integer)
    max_classes_per_day: Mapped[int] = mapped_column(Integer, server_default="4")
    subjects_can_teach: Mapped[Optional[dict]] = mapped_column(JSON)
    active: Mapped[int] = mapped_column(Integer, server_default="1")

    department = relationship("Departments", back_populates="faculty")
    faculty_unavailability = relationship("FacultyUnavailability", back_populates="faculty")
    faculty_assignments = relationship("FacultyAssignments", back_populates="faculty")


class Subjects(Base):
    __tablename__ = 'subjects'

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(Enum("theory", "lab", name="subject_type"))
    classes_per_week: Mapped[int] = mapped_column(Integer, server_default="3")
    duration_slots: Mapped[int] = mapped_column(Integer, server_default="1")
    department_id: Mapped[Optional[int]] = mapped_column(Integer)

    department = relationship("Departments", back_populates="subjects")
    subject_offerings = relationship("SubjectOfferings", back_populates="subjects")


class FacultyUnavailability(Base):
    __tablename__ = 'faculty_unavailability'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    faculty_id: Mapped[int] = mapped_column(Integer)
    date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    day: Mapped[Optional[int]] = mapped_column(Integer)
    slot: Mapped[Optional[int]] = mapped_column(Integer)
    reason: Mapped[Optional[str]] = mapped_column(String(200))

    faculty = relationship("Faculty", back_populates="faculty_unavailability")


class SubjectOfferings(Base):
    __tablename__ = 'subject_offerings'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_code: Mapped[str] = mapped_column(String(32))
    batch_id: Mapped[int] = mapped_column(Integer)
    semester: Mapped[int] = mapped_column(Integer)
    elective: Mapped[int] = mapped_column(Integer, server_default="0")

    batch = relationship("Batches", back_populates="subject_offerings")
    subjects = relationship("Subjects", back_populates="subject_offerings")
    faculty_assignments = relationship("FacultyAssignments", back_populates="subject_offering")
    fixed_slots = relationship("FixedSlots", back_populates="subject_offering")


class FacultyAssignments(Base):
    __tablename__ = 'faculty_assignments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_offering_id: Mapped[int] = mapped_column(Integer)
    faculty_id: Mapped[int] = mapped_column(Integer)
    preference_score: Mapped[Optional[decimal.Decimal]] = mapped_column(DECIMAL(4, 2))

    faculty = relationship("Faculty", back_populates="faculty_assignments")
    subject_offering = relationship("SubjectOfferings", back_populates="faculty_assignments")


class FixedSlots(Base):
    __tablename__ = 'fixed_slots'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_offering_id: Mapped[int] = mapped_column(Integer)
    day: Mapped[int] = mapped_column(Integer)
    slot: Mapped[int] = mapped_column(Integer)
    room_id: Mapped[Optional[int]] = mapped_column(Integer)
    reason: Mapped[Optional[str]] = mapped_column(String(200))

    room = relationship("Rooms", back_populates="fixed_slots")
    subject_offering = relationship("SubjectOfferings", back_populates="fixed_slots")


# CREATE TABLES FOR ANY DATABASE ENGINE
Base.metadata.create_all(bind=engine)
