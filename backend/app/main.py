"""main.py — FastAPI application entrypoint.

Startup sequence:
  1. Create all SQLModel tables (auto-migration for dev / SQLite).
  2. Register all API routers under /api/v1.
  3. Configure CORS (allow all origins in dev; restrict in prod via env).

Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import (
    assignments,
    auth,
    departments,
    marks,
    reports,
    sections,
    students,
    subjects,
    users,
)

# ---------------------------------------------------------------------------
# Lifespan — database init on startup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run startup and shutdown tasks."""
    init_db()  # Create tables if they do not yet exist (SQLite dev mode)
    yield
    # Teardown (if needed) goes here


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


app = FastAPI(
    title=settings.app_name,
    description=(
        'REST API for the Student Mark Attainment System with Institutional '
        'Role Hierarchy (SuperAdmin -> HOD -> Faculty -> Student). '
        'Manages departments, classes/sections, subjects, students, marks entry, '
        'CO attainment calculation, and reporting/export.'
    ),
    version='2.0.0',
    lifespan=lifespan,
    docs_url='/docs',
    redoc_url='/redoc',
)

# ---------------------------------------------------------------------------
# CORS — allow the Next.js dev server and any configured origins
# ---------------------------------------------------------------------------

_CORS_ORIGINS = [
    'http://localhost:3000',   # Next.js dev server
    'http://localhost:3001',
    'http://127.0.0.1:3000',
]

if settings.env == 'dev':
    # In development, allow all origins for convenience
    _CORS_ORIGINS = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# ---------------------------------------------------------------------------
# Routers — all mounted under /api/v1
# ---------------------------------------------------------------------------

API_PREFIX = '/api/v1'

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(departments.router, prefix=API_PREFIX)
app.include_router(sections.router, prefix=API_PREFIX)
app.include_router(subjects.router, prefix=API_PREFIX)
app.include_router(students.router, prefix=API_PREFIX)
app.include_router(assignments.router, prefix=API_PREFIX)
app.include_router(marks.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get('/health', tags=['Health'])
def health_check() -> dict:
    """Lightweight liveness probe endpoint."""
    return {'status': 'ok', 'app': settings.app_name, 'env': settings.env}


# ---------------------------------------------------------------------------
# Dev-only seed endpoint
# ---------------------------------------------------------------------------


if settings.env == 'dev':
    from sqlmodel import Session, select as _select

    from app.core.security import get_password_hash as _hash
    from app.database import engine as _engine
    from app.models.department import Department as _Dept
    from app.models.faculty_subject_assignment import FacultySubjectAssignment as _FSA
    from app.models.section import Section as _Section, SectionStudents as _SectionStudents
    from app.models.student import Student as _Student
    from app.models.student_marks import StudentMarks as _StudentMarks
    from app.models.subject import Subject as _Subject
    from app.models.user import User as _User, UserRole as _Role

    @app.post('/dev/seed', tags=['Dev'], summary='Seed demo data (dev only)')
    def seed_demo_data() -> dict:
        """Create a default SuperAdmin, HOD, Faculty, Department, Section, Subject, Students, and sample Marks.

        Safe to call multiple times — skips records that already exist.
        Only available when ENV=dev.
        """
        created: list[str] = []

        with Session(_engine) as db:
            # 1. Department
            dept = db.exec(_select(_Dept).where(_Dept.code == 'CSE')).first()
            if dept is None:
                dept = _Dept(
                    name='Computer Science and Engineering',
                    code='CSE',
                )
                db.add(dept)
                db.flush()
                created.append('department: CSE - Computer Science and Engineering')

            # 2. Super Admin
            super_admin = db.exec(_select(_User).where(_User.email == 'superadmin@demo.com')).first()
            if super_admin is None:
                super_admin = _User(
                    name='Principal SuperAdmin',
                    email='superadmin@demo.com',
                    password_hash=_hash('SuperAdmin@1234'),
                    role=_Role.SUPER_ADMIN,
                )
                db.add(super_admin)
                db.flush()
                created.append('super_admin: superadmin@demo.com / SuperAdmin@1234')

            # Legacy Admin
            admin = db.exec(_select(_User).where(_User.email == 'admin@demo.com')).first()
            if admin is None:
                admin = _User(
                    name='Demo Admin',
                    email='admin@demo.com',
                    password_hash=_hash('Admin@1234'),
                    role=_Role.ADMIN,
                )
                db.add(admin)
                db.flush()
                created.append('admin: admin@demo.com / Admin@1234')

            # 3. HOD
            hod = db.exec(_select(_User).where(_User.email == 'hod@demo.com')).first()
            if hod is None:
                hod = _User(
                    name='Dr. Meena (HOD CSE)',
                    email='hod@demo.com',
                    password_hash=_hash('Hod@1234'),
                    role=_Role.HOD,
                    department_id=dept.id,
                )
                db.add(hod)
                db.flush()
                dept.hod_id = hod.id
                db.add(dept)
                created.append('hod: hod@demo.com / Hod@1234')

            # 4. Faculty
            faculty = db.exec(_select(_User).where(_User.email == 'faculty@demo.com')).first()
            if faculty is None:
                faculty = _User(
                    name='Dr. Ramesh (Faculty)',
                    email='faculty@demo.com',
                    password_hash=_hash('Faculty@1234'),
                    role=_Role.FACULTY,
                    department_id=dept.id,
                )
                db.add(faculty)
                db.flush()
                created.append('faculty: faculty@demo.com / Faculty@1234')

            # 5. Section (Class)
            section = db.exec(
                _select(_Section).where(
                    _Section.name == 'III-CSE-A',
                    _Section.department_id == dept.id,
                )
            ).first()
            if section is None:
                section = _Section(
                    name='III-CSE-A',
                    department_id=dept.id,
                    semester=3,
                    academic_year='2025-26',
                )
                db.add(section)
                db.flush()
                created.append('section: III-CSE-A (Semester 3, 2025-26)')

            # 6. Subject
            subject = db.exec(
                _select(_Subject).where(_Subject.course_code == 'CS301')
            ).first()
            if subject is None:
                subject = _Subject(
                    course_code='CS301',
                    course_name='Data Structures and Algorithms',
                    department_id=dept.id,
                    semester=3,
                )
                db.add(subject)
                db.flush()
                created.append('subject: CS301 - Data Structures and Algorithms')

            # 7. Faculty-Subject-Section Assignment
            assign = db.exec(
                _select(_FSA).where(
                    _FSA.faculty_id == faculty.id,
                    _FSA.subject_id == subject.id,
                    _FSA.section_id == section.id,
                )
            ).first()
            if assign is None:
                assign = _FSA(
                    faculty_id=faculty.id,
                    subject_id=subject.id,
                    section_id=section.id,
                    academic_year='2025-26',
                )
                db.add(assign)
                db.flush()
                created.append('assignment: faculty@demo.com -> CS301 -> III-CSE-A (2025-26)')

            # 8. Sample students + section enrollment + marks
            sample_students = [
                ('S001', 'REG2025001', 'Alice Johnson', 30, 8, 75, 80, 15),
                ('S002', 'REG2025002', 'Bob Smith',     28, 7, 70, 72, 13),
                ('S003', 'REG2025003', 'Clara Patel',   35, 9, 88, 90, 18),
            ]
            for roll, reg, name, cia, assess, pres, quiz, endsem in sample_students:
                st = db.exec(_select(_Student).where(_Student.roll_num == roll)).first()
                if st is None:
                    st = _Student(
                        roll_num=roll,
                        register_num=reg,
                        name=name,
                        department='CSE',
                        semester=3,
                    )
                    db.add(st)
                    db.flush()
                    created.append(f'student: {name} ({roll})')

                # Enroll in section
                enrolled = db.exec(
                    _select(_SectionStudents).where(
                        _SectionStudents.section_id == section.id,
                        _SectionStudents.student_id == st.id,
                    )
                ).first()
                if enrolled is None:
                    enrolled = _SectionStudents(section_id=section.id, student_id=st.id)
                    db.add(enrolled)
                    db.flush()
                    created.append(f'enrolled: {name} -> {section.name}')

                marks_exists = db.exec(
                    _select(_StudentMarks).where(
                        _StudentMarks.student_id == st.id,
                        _StudentMarks.subject_id == subject.id,
                    )
                ).first()
                if marks_exists is None:
                    from app.services.calculation_service import (
                        apply_attainment_to_marks_row as _apply,
                        calculate_attainment as _calc,
                    )

                    result = _calc(
                        cia_co1=cia, cia_co2=cia - 2, cia_co3=cia - 1, cia_co4=cia, cia_co5=cia - 3,
                        assess_co1=assess, assess_co2=assess - 1, assess_co3=assess,
                        assess_co4=assess - 2, assess_co5=assess,
                        presentation=pres, quiz=quiz,
                        endsem_co1=endsem, endsem_co2=endsem - 1, endsem_co3=endsem,
                        endsem_co4=endsem - 2, endsem_co5=endsem,
                    )
                    m = _StudentMarks(
                        student_id=st.id,
                        subject_id=subject.id,
                        section_id=section.id,
                        entered_by_faculty_id=faculty.id,
                        cia_co1=cia, cia_co2=cia - 2, cia_co3=cia - 1, cia_co4=cia, cia_co5=cia - 3,
                        assess_co1=assess, assess_co2=assess - 1, assess_co3=assess,
                        assess_co4=assess - 2, assess_co5=assess,
                        presentation=pres, quiz=quiz,
                        endsem_co1=endsem, endsem_co2=endsem - 1, endsem_co3=endsem,
                        endsem_co4=endsem - 2, endsem_co5=endsem,
                    )
                    _apply(m, result)
                    db.add(m)
                    created.append(f'marks: {name} -> CS301 (section {section.name})')

            db.commit()

        return {
            'seeded': len(created),
            'details': created if created else ['All records already exist — nothing to seed'],
        }
