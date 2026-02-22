from __future__ import annotations
from datetime import date, time, datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID


class Student(BaseModel):
    id: Optional[UUID] = None
    first_name: str
    last_name: str
    grade_level: int = Field(ge=1, le=12)
    date_of_birth: Optional[date] = None
    parent_name: Optional[str] = None
    parent_email: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Course(BaseModel):
    id: Optional[UUID] = None
    code: str
    title: str
    subject: str
    grade_level_min: int = Field(ge=1, le=12)
    grade_level_max: int = Field(ge=1, le=12)
    description: Optional[str] = None
    duration_weeks: int = 12
    hours_per_week: float = 3.0
    difficulty: str = "standard"
    prerequisites: list[str] = []
    tags: list[str] = []
    is_active: bool = True
    created_at: Optional[datetime] = None


class Availability(BaseModel):
    id: Optional[UUID] = None
    student_id: UUID
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    preference: str = "available"


class Schedule(BaseModel):
    id: Optional[UUID] = None
    student_id: UUID
    course_id: UUID
    status: str = "proposed"
    start_date: date
    end_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ScheduleSlot(BaseModel):
    id: Optional[UUID] = None
    schedule_id: UUID
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    location: str = "Home"


class GeneratedPDF(BaseModel):
    id: Optional[UUID] = None
    student_id: Optional[UUID] = None
    course_id: Optional[UUID] = None
    pdf_type: str
    title: str
    minio_bucket: str = "evlin-pdfs"
    minio_key: str
    file_size_kb: Optional[int] = None
    page_count: Optional[int] = None
    metadata: dict = {}
    created_at: Optional[datetime] = None


class OCRDocument(BaseModel):
    id: Optional[UUID] = None
    original_filename: str
    minio_key: str
    extracted_text: Optional[str] = None
    confidence: Optional[float] = None
    status: str = "pending"
    processed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class SessionInstance(BaseModel):
    id: Optional[UUID] = None
    schedule_id: UUID
    schedule_slot_id: UUID
    session_date: date
    start_time: time
    end_time: time
    status: str = "pending"  # pending | completed | missed | rescheduled | cancelled
    checked_in_at: Optional[datetime] = None
    rescheduled_from: Optional[UUID] = None
    rescheduled_to: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class CheckinLog(BaseModel):
    id: Optional[UUID] = None
    session_instance_id: UUID
    action: str  # check_in | auto_miss | reschedule | cancel
    performed_by: Optional[str] = None
    details: dict = {}
    created_at: Optional[datetime] = None


class AgentConversation(BaseModel):
    id: Optional[UUID] = None
    student_id: Optional[UUID] = None
    agent_type: str
    messages: list[dict] = []
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
