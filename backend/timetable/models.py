from typing import Optional
import datetime
import decimal
import os
from sqlalchemy import CheckConstraint, DECIMAL, Date, Enum, ForeignKeyConstraint, Index, Integer, JSON, String, Text, Time, text, create_engine # pyright: ignore[reportMissingImports]
from sqlalchemy.dialects.mysql import TINYINT # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker # pyright: ignore[reportMissingImports]

# Load DB info from env or hardcode for now
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "binatlos")
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "college")

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

#SqlAlchemy ORM models


class Config(Base):
    __tablename__ = 'config'

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text)


class Departments(Base):
    __tablename__ = 'departments'
    __table_args__ = (
        Index('code', 'code', unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    batches: Mapped[list['Batches']] = relationship('Batches', back_populates='department')
    faculty: Mapped[list['Faculty']] = relationship('Faculty', back_populates='department')
    subjects: Mapped[list['Subjects']] = relationship('Subjects', back_populates='department')


class Rooms(Base):
    __tablename__ = 'rooms'
    __table_args__ = (
        Index('code', 'code', unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(Enum('theory', 'lab'), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(128))

    fixed_slots: Mapped[list['FixedSlots']] = relationship('FixedSlots', back_populates='room')


class Timeslots(Base):
    __tablename__ = 'timeslots'
    __table_args__ = (
        Index('day', 'day', 'slot', unique=True),
        Index('idx_timeslot_day_slot', 'day', 'slot')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[int] = mapped_column(TINYINT, nullable=False)
    slot: Mapped[int] = mapped_column(TINYINT, nullable=False)
    start_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    end_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)


class Batches(Base):
    __tablename__ = 'batches'
    __table_args__ = (
        ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL', name='batches_ibfk_1'),
        Index('idx_batches_dept', 'department_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(Integer)
    shift: Mapped[Optional[str]] = mapped_column(Enum('day', 'evening'), server_default=text("'day'"))

    department: Mapped[Optional['Departments']] = relationship('Departments', back_populates='batches')
    subject_offerings: Mapped[list['SubjectOfferings']] = relationship('SubjectOfferings', back_populates='batch')


class Faculty(Base):
    __tablename__ = 'faculty'
    __table_args__ = (
        ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL', name='faculty_ibfk_1'),
        Index('email', 'email', unique=True),
        Index('idx_faculty_dept', 'department_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(150))
    department_id: Mapped[Optional[int]] = mapped_column(Integer)
    max_classes_per_day: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'4'"))
    subjects_can_teach: Mapped[Optional[dict]] = mapped_column(JSON)
    active: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))

    department: Mapped[Optional['Departments']] = relationship('Departments', back_populates='faculty')
    faculty_unavailability: Mapped[list['FacultyUnavailability']] = relationship('FacultyUnavailability', back_populates='faculty')
    faculty_assignments: Mapped[list['FacultyAssignments']] = relationship('FacultyAssignments', back_populates='faculty')


class Subjects(Base):
    __tablename__ = 'subjects'
    __table_args__ = (
        ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL', name='subjects_ibfk_1'),
        Index('department_id', 'department_id')
    )

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(Enum('theory', 'lab'), nullable=False)
    classes_per_week: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("'3'"))
    duration_slots: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("'1'"))
    department_id: Mapped[Optional[int]] = mapped_column(Integer)

    department: Mapped[Optional['Departments']] = relationship('Departments', back_populates='subjects')
    subject_offerings: Mapped[list['SubjectOfferings']] = relationship('SubjectOfferings', back_populates='subjects')


class FacultyUnavailability(Base):
    __tablename__ = 'faculty_unavailability'
    __table_args__ = (
        CheckConstraint('((`date` is not null) or (`day` is not null) or (`slot` is null))', name='faculty_unavailability_chk_1'),
        ForeignKeyConstraint(['faculty_id'], ['faculty.id'], ondelete='CASCADE', name='faculty_unavailability_ibfk_1'),
        Index('faculty_id', 'faculty_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    faculty_id: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    day: Mapped[Optional[int]] = mapped_column(TINYINT)
    slot: Mapped[Optional[int]] = mapped_column(TINYINT)
    reason: Mapped[Optional[str]] = mapped_column(String(200))

    faculty: Mapped['Faculty'] = relationship('Faculty', back_populates='faculty_unavailability')


class SubjectOfferings(Base):
    __tablename__ = 'subject_offerings'
    __table_args__ = (
        ForeignKeyConstraint(['batch_id'], ['batches.id'], ondelete='CASCADE', name='subject_offerings_ibfk_2'),
        ForeignKeyConstraint(['subject_code'], ['subjects.code'], ondelete='CASCADE', name='subject_offerings_ibfk_1'),
        Index('idx_offerings_batch', 'batch_id'),
        Index('subject_code', 'subject_code')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_code: Mapped[str] = mapped_column(String(32), nullable=False)
    batch_id: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    elective: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))

    batch: Mapped['Batches'] = relationship('Batches', back_populates='subject_offerings')
    subjects: Mapped['Subjects'] = relationship('Subjects', back_populates='subject_offerings')
    faculty_assignments: Mapped[list['FacultyAssignments']] = relationship('FacultyAssignments', back_populates='subject_offering')
    fixed_slots: Mapped[list['FixedSlots']] = relationship('FixedSlots', back_populates='subject_offering')


class FacultyAssignments(Base):
    __tablename__ = 'faculty_assignments'
    __table_args__ = (
        ForeignKeyConstraint(['faculty_id'], ['faculty.id'], ondelete='CASCADE', name='faculty_assignments_ibfk_2'),
        ForeignKeyConstraint(['subject_offering_id'], ['subject_offerings.id'], ondelete='CASCADE', name='faculty_assignments_ibfk_1'),
        Index('faculty_id', 'faculty_id'),
        Index('subject_offering_id', 'subject_offering_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_offering_id: Mapped[int] = mapped_column(Integer, nullable=False)
    faculty_id: Mapped[int] = mapped_column(Integer, nullable=False)
    preference_score: Mapped[Optional[decimal.Decimal]] = mapped_column(DECIMAL(4, 2))

    faculty: Mapped['Faculty'] = relationship('Faculty', back_populates='faculty_assignments')
    subject_offering: Mapped['SubjectOfferings'] = relationship('SubjectOfferings', back_populates='faculty_assignments')


class FixedSlots(Base):
    __tablename__ = 'fixed_slots'
    __table_args__ = (
        ForeignKeyConstraint(['room_id'], ['rooms.id'], ondelete='SET NULL', name='fixed_slots_ibfk_2'),
        ForeignKeyConstraint(['subject_offering_id'], ['subject_offerings.id'], ondelete='CASCADE', name='fixed_slots_ibfk_1'),
        Index('room_id', 'room_id'),
        Index('subject_offering_id', 'subject_offering_id', 'day', 'slot', unique=True)
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_offering_id: Mapped[int] = mapped_column(Integer, nullable=False)
    day: Mapped[int] = mapped_column(TINYINT, nullable=False)
    slot: Mapped[int] = mapped_column(TINYINT, nullable=False)
    room_id: Mapped[Optional[int]] = mapped_column(Integer)
    reason: Mapped[Optional[str]] = mapped_column(String(200))

    room: Mapped[Optional['Rooms']] = relationship('Rooms', back_populates='fixed_slots')
    subject_offering: Mapped['SubjectOfferings'] = relationship('SubjectOfferings', back_populates='fixed_slots')
