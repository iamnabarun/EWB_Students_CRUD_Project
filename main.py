from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
import sqlite3
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "students.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date_of_birth TEXT NOT NULL,
                email TEXT UNIQUE,
                phone TEXT,
                course TEXT,
                address TEXT,
                enrollment_date TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (email IS NOT NULL OR phone IS NOT NULL)
            )
        """)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Students Database CRUD API",
    description="A simple student-record management API built with FastAPI and SQLite.",
    version="1.0.0",
    lifespan=lifespan,
)


class StudentBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100, examples=["Aarav Sharma"])
    date_of_birth: date = Field(examples=["2005-04-18"])
    email: Optional[str] = Field(default=None, max_length=254, examples=["aarav@example.com"])
    phone: Optional[str] = Field(default=None, max_length=25, examples=["+91-9876543210"])
    course: Optional[str] = Field(default=None, max_length=100, examples=["Computer Science"])
    address: Optional[str] = Field(default=None, max_length=300)
    enrollment_date: Optional[date] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        if value is not None:
            value = value.strip().lower()
            if value.count("@") != 1 or "." not in value.rsplit("@", 1)[-1] or " " in value:
                raise ValueError("Enter a valid email address")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value):
        if value is not None and not any(ch.isdigit() for ch in value):
            raise ValueError("Phone must contain at least one digit")
        return value

    @model_validator(mode="after")
    def require_contact(self):
        if not self.email and not self.phone:
            raise ValueError("Provide at least one contact method: email or phone")
        return self


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    email: Optional[str] = Field(default=None, max_length=254)
    phone: Optional[str] = Field(default=None, max_length=25)
    course: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=300)
    enrollment_date: Optional[date] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        if value is not None:
            value = value.strip().lower()
            if value.count("@") != 1 or "." not in value.rsplit("@", 1)[-1] or " " in value:
                raise ValueError("Enter a valid email address")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value):
        if value is not None and not any(ch.isdigit() for ch in value):
            raise ValueError("Phone must contain at least one digit")
        return value


class StudentOut(BaseModel):
    student_id: int
    name: str
    date_of_birth: date
    email: Optional[str] = None
    phone: Optional[str] = None
    course: Optional[str] = None
    address: Optional[str] = None
    enrollment_date: Optional[date] = None
    created_at: str


def row_to_student(row):
    if row is None:
        return None
    data = dict(row)
    return data


def get_student_or_404(student_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Student with ID {student_id} was not found")
    return row_to_student(row)


@app.get("/", tags=["General"])
def root():
    return {"message": "Students CRUD API is running", "docs": "/docs"}


@app.post("/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED, tags=["Students"])
def create_student(student: StudentCreate):
    data = student.model_dump(mode="json")
    try:
        with get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO students (name, date_of_birth, email, phone, course, address, enrollment_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data["name"], data["date_of_birth"], data["email"], data["phone"],
                  data["course"], data["address"], data["enrollment_date"]))
            student_id = cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        if "students.email" in str(exc) or "UNIQUE constraint failed" in str(exc):
            raise HTTPException(status_code=409, detail="A student with this email already exists") from exc
        raise HTTPException(status_code=422, detail="Student record violates a database constraint") from exc
    return get_student_or_404(student_id)


@app.get("/students", response_model=list[StudentOut], tags=["Students"])
def list_students(
    name: Optional[str] = Query(default=None, description="Case-insensitive partial name match"),
    course: Optional[str] = Query(default=None, description="Case-insensitive partial course match"),
    born_after: Optional[date] = Query(default=None, description="Return students born after this date"),
    born_before: Optional[date] = Query(default=None, description="Return students born before this date"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    conditions, params = [], []
    if name:
        conditions.append("LOWER(name) LIKE ?")
        params.append(f"%{name.lower()}%")
    if course:
        conditions.append("LOWER(COALESCE(course, '')) LIKE ?")
        params.append(f"%{course.lower()}%")
    if born_after:
        conditions.append("date_of_birth > ?")
        params.append(born_after.isoformat())
    if born_before:
        conditions.append("date_of_birth < ?")
        params.append(born_before.isoformat())
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM students{where} ORDER BY student_id LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
    return [row_to_student(row) for row in rows]


@app.get("/students/{student_id}", response_model=StudentOut, tags=["Students"])
def get_student(student_id: int):
    return get_student_or_404(student_id)


@app.put("/students/{student_id}", response_model=StudentOut, tags=["Students"])
def replace_student(student_id: int, student: StudentCreate):
    get_student_or_404(student_id)
    data = student.model_dump(mode="json")
    try:
        with get_connection() as conn:
            conn.execute("""
                UPDATE students SET name=?, date_of_birth=?, email=?, phone=?, course=?, address=?, enrollment_date=?
                WHERE student_id=?
            """, (data["name"], data["date_of_birth"], data["email"], data["phone"],
                  data["course"], data["address"], data["enrollment_date"], student_id))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="A student with this email already exists") from exc
    return get_student_or_404(student_id)


@app.patch("/students/{student_id}", response_model=StudentOut, tags=["Students"])
def update_student(student_id: int, student: StudentUpdate):
    current = get_student_or_404(student_id)
    changes = student.model_dump(exclude_unset=True, mode="json")
    if not changes:
        raise HTTPException(status_code=400, detail="Provide at least one field to update")
    if any(changes.get(field, "__missing__") is None for field in ("name", "date_of_birth")):
        raise HTTPException(status_code=422, detail="Name and date_of_birth cannot be null")
    updated = {**current, **changes}
    if not updated.get("email") and not updated.get("phone"):
        raise HTTPException(status_code=422, detail="A student must have an email or phone number")
    allowed = {"name", "date_of_birth", "email", "phone", "course", "address", "enrollment_date"}
    columns = [key for key in changes if key in allowed]
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE students SET " + ", ".join(f"{key} = ?" for key in columns) + " WHERE student_id = ?",
                [updated[key] for key in columns] + [student_id],
            )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="A student with this email already exists") from exc
    return get_student_or_404(student_id)


@app.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Students"])
def delete_student(student_id: int):
    get_student_or_404(student_id)
    with get_connection() as conn:
        conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
