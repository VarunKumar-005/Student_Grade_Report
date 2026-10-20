"""conftest.py — Shared pytest fixtures for backend tests.

Sets up an in-memory SQLite test database and an HTTPX TestClient
that uses it, so tests run completely isolated from any dev database.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.security import get_password_hash
from app.database import get_session
from app.main import app
from app.models.department import Department
from app.models.faculty_subject_assignment import FacultySubjectAssignment
from app.models.section import Section
from app.models.subject import Subject
from app.models.user import User, UserRole

# ---------------------------------------------------------------------------
# In-memory test engine
# ---------------------------------------------------------------------------


@pytest.fixture(name='engine', scope='session')
def engine_fixture():
    """Create a shared, in-memory SQLite engine for the test session."""
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


from sqlalchemy import text
from app.deps import get_db


@pytest.fixture(name='db')
def db_fixture(engine):
    """Provide a clean database schema and fresh Session for each test."""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = OFF;"))
        for table in SQLModel.metadata.tables.values():
            conn.execute(table.delete())
        conn.execute(text("PRAGMA foreign_keys = ON;"))
        conn.commit()


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------


@pytest.fixture(name='client')
def client_fixture(engine):
    """TestClient with the DB session overridden to use the test engine."""

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


@pytest.fixture(name='department')
def department_fixture(db: Session) -> Department:
    """Create and persist a test department."""
    dept = Department(name='Computer Science and Engineering', code='CSE')
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@pytest.fixture(name='section')
def section_fixture(db: Session, department: Department) -> Section:
    """Create and persist a test section."""
    sec = Section(
        name='III-CSE-A',
        department_id=department.id,
        semester=3,
        academic_year='2025-26',
    )
    db.add(sec)
    db.commit()
    db.refresh(sec)
    return sec


@pytest.fixture(name='subject')
def subject_fixture(db: Session, department: Department) -> Subject:
    """Create and persist a test subject."""
    sub = Subject(
        course_code='CS101',
        course_name='Intro to CS',
        department_id=department.id,
        semester=1,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@pytest.fixture(name='faculty_assignment')
def faculty_assignment_fixture(
    db: Session,
    faculty_user: User,
    subject: Subject,
    section: Section,
) -> FacultySubjectAssignment:
    """Assign faculty to test subject and section."""
    fa = FacultySubjectAssignment(
        faculty_id=faculty_user.id,
        subject_id=subject.id,
        section_id=section.id,
        academic_year='2025-26',
    )
    db.add(fa)
    db.commit()
    db.refresh(fa)
    return fa



@pytest.fixture(name='super_admin_user')
def super_admin_user_fixture(db: Session) -> User:
    """Create and persist a test Super Admin user."""
    user = User(
        name='Test SuperAdmin',
        email='superadmin@test.com',
        password_hash=get_password_hash('superadminpass'),
        role=UserRole.SUPER_ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(name='admin_user')
def admin_user_fixture(db: Session) -> User:
    """Create and persist a test admin user."""
    user = User(
        name='Test Admin',
        email='admin@test.com',
        password_hash=get_password_hash('adminpass'),
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(name='hod_user')
def hod_user_fixture(db: Session, department: Department) -> User:
    """Create and persist a test HOD user."""
    user = User(
        name='Test HOD',
        email='hod@test.com',
        password_hash=get_password_hash('hodpass'),
        role=UserRole.HOD,
        department_id=department.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    department.hod_id = user.id
    db.add(department)
    db.commit()
    return user


@pytest.fixture(name='faculty_user')
def faculty_user_fixture(db: Session, department: Department) -> User:
    """Create and persist a test faculty user."""
    user = User(
        name='Test Faculty',
        email='faculty@test.com',
        password_hash=get_password_hash('facultypass'),
        role=UserRole.FACULTY,
        department_id=department.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(name='super_admin_token')
def super_admin_token_fixture(client: TestClient, super_admin_user: User) -> str:
    """Log in as super admin and return the JWT access token."""
    resp = client.post(
        '/api/v1/auth/login',
        json={'email': 'superadmin@test.com', 'password': 'superadminpass'},
    )
    assert resp.status_code == 200
    return resp.json()['access_token']


@pytest.fixture(name='admin_token')
def admin_token_fixture(client: TestClient, admin_user: User) -> str:
    """Log in as admin and return the JWT access token."""
    resp = client.post(
        '/api/v1/auth/login',
        json={'email': 'admin@test.com', 'password': 'adminpass'},
    )
    assert resp.status_code == 200
    return resp.json()['access_token']


@pytest.fixture(name='hod_token')
def hod_token_fixture(client: TestClient, hod_user: User) -> str:
    """Log in as HOD and return the JWT access token."""
    resp = client.post(
        '/api/v1/auth/login',
        json={'email': 'hod@test.com', 'password': 'hodpass'},
    )
    assert resp.status_code == 200
    return resp.json()['access_token']


@pytest.fixture(name='faculty_token')
def faculty_token_fixture(client: TestClient, faculty_user: User) -> str:
    """Log in as faculty and return the JWT access token."""
    resp = client.post(
        '/api/v1/auth/login',
        json={'email': 'faculty@test.com', 'password': 'facultypass'},
    )
    assert resp.status_code == 200
    return resp.json()['access_token']
