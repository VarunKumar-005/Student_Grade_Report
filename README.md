# Student Mark Attainment System

A centralized, web-based student mark database system that helps college faculties enter, calculate, and retrieve student marks — automating Course Outcome (CO) attainment calculations and replacing manual spreadsheet workflows.

## Tech Stack

- **Backend:** Python (FastAPI) — ASGI support, automatic Pydantic validation
- **Database:** Neon (Serverless PostgreSQL) via SQLAlchemy / SQLModel
- **Frontend:** Next.js + Tailwind CSS + shadcn/ui

---

## ER Diagram

```mermaid
erDiagram
    USERS ||--o{ FACULTY_SUBJECT_ASSIGNMENTS : "assigned as faculty"
    SUBJECTS ||--o{ FACULTY_SUBJECT_ASSIGNMENTS : "assigned to faculty"
    SUBJECTS ||--o{ STUDENT_MARKS : "has marks recorded for"
    STUDENTS ||--o{ STUDENT_MARKS : "has marks in"

    USERS {
        int id PK
        varchar name
        varchar email UK
        varchar password_hash
        varchar role "ADMIN or FACULTY"
    }

    SUBJECTS {
        int id PK
        varchar course_code UK
        varchar course_name
        varchar department
        int semester
    }

    FACULTY_SUBJECT_ASSIGNMENTS {
        int id PK
        int faculty_id FK
        int subject_id FK
        varchar academic_year
    }

    STUDENTS {
        int id PK
        varchar roll_num UK
        varchar register_num UK
        varchar name
        varchar department
        int semester
    }

    STUDENT_MARKS {
        int id PK
        int student_id FK
        int subject_id FK
        numeric cia_co1
        numeric cia_co2
        numeric cia_co3
        numeric cia_co4
        numeric cia_co5
        numeric ass_co1
        numeric ass_co2
        numeric ass_co3
        numeric ass_co4
        numeric ass_co5
        numeric presentation
        numeric quiz
        numeric endsem_co1
        numeric endsem_co2
        numeric endsem_co3
        numeric endsem_co4
        numeric endsem_co5
        numeric internal_x
        numeric endsem_y
        numeric direct_attainment
    }
```

---

## System Architecture

```mermaid
flowchart TB
    subgraph Clients["Client Layer"]
        AdminUI["Admin Dashboard<br/>(Next.js + Tailwind + shadcn/ui)"]
        FacultyUI["Faculty Dashboard<br/>(Next.js + Tailwind + shadcn/ui)"]
    end

    subgraph EdgeAuth["Auth / Middleware"]
        AuthMW["Next.js Middleware<br/>Route Guards (ADMIN / FACULTY)"]
        JWT["JWT / Session Auth"]
    end

    subgraph Backend["Backend Layer - FastAPI (ASGI)"]
        API["REST API<br/>(Pydantic validation)"]
        AuthSvc["Auth Service<br/>(login, roles, JWT issuance)"]
        UserSvc["User & Assignment Service<br/>(Admin: manage faculty, subjects, students)"]
        MarksSvc["Marks Entry Service<br/>(Faculty: CIA, Assignment, Presentation, Quiz, EndSem)"]
        CalcSvc["Attainment Calculation Engine<br/>(Internal X, EndSem Y, Direct Attainment)"]
        ReportSvc["Reporting / Export Service<br/>(CSV / PDF / dashboard views)"]
    end

    subgraph Data["Database Layer"]
        DB[("Neon Serverless PostgreSQL<br/>via SQLAlchemy / SQLModel")]
    end

    AdminUI -->|HTTPS requests| AuthMW
    FacultyUI -->|HTTPS requests| AuthMW
    AuthMW --> JWT
    JWT --> API

    API --> AuthSvc
    API --> UserSvc
    API --> MarksSvc
    API --> ReportSvc

    MarksSvc --> CalcSvc
    CalcSvc --> DB
    AuthSvc --> DB
    UserSvc --> DB
    MarksSvc --> DB
    ReportSvc --> DB

    DB -->|calculated results| ReportSvc
    ReportSvc -->|attainment reports| AdminUI
    ReportSvc -->|subject-wise reports| FacultyUI
```

---

## Folder Structure

```
student-mark-attainment-system/
│
├── backend/                          # FastAPI service
│   ├── app/
│   │   ├── main.py                   # FastAPI app entrypoint, router registration
│   │   ├── config.py                 # env vars, settings (DB URL, JWT secret, etc.)
│   │   ├── database.py               # SQLAlchemy/SQLModel engine + session
│   │   │
│   │   ├── models/                   # SQLModel/SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── subject.py
│   │   │   ├── student.py
│   │   │   ├── faculty_subject_assignment.py
│   │   │   └── student_marks.py
│   │   │
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   │   ├── user.py
│   │   │   ├── subject.py
│   │   │   ├── student.py
│   │   │   └── marks.py
│   │   │
│   │   ├── routers/                  # API route handlers, grouped by resource
│   │   │   ├── auth.py               # login, token refresh
│   │   │   ├── users.py              # admin: manage faculty accounts
│   │   │   ├── subjects.py           # admin: manage subjects
│   │   │   ├── students.py           # admin: manage students
│   │   │   ├── assignments.py        # admin: assign faculty to subjects
│   │   │   ├── marks.py              # faculty: enter/edit marks
│   │   │   └── reports.py            # both: attainment reports, exports
│   │   │
│   │   ├── services/                 # business logic, kept out of routers
│   │   │   ├── auth_service.py       # JWT issuance, password hashing
│   │   │   ├── calculation_service.py # Internal X, EndSem Y, Direct Attainment
│   │   │   └── report_service.py     # CSV/PDF export logic
│   │   │
│   │   ├── core/
│   │   │   ├── security.py           # JWT decode, password hashing helpers
│   │   │   └── permissions.py        # role-based access control (ADMIN/FACULTY)
│   │   │
│   │   └── deps.py                   # shared FastAPI dependencies (get_db, get_current_user)
│   │
│   ├── alembic/                      # DB migrations
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── tests/
│   │   ├── test_auth.py
│   │   ├── test_marks.py
│   │   └── test_calculation_service.py
│   │
│   ├── requirements.txt
│   ├── alembic.ini
│   └── .env
│
├── frontend/                         # Next.js app
│   ├── app/
│   │   ├── (auth)/
│   │   │   └── login/page.tsx
│   │   │
│   │   ├── (admin)/
│   │   │   ├── dashboard/page.tsx
│   │   │   ├── faculty/page.tsx      # manage faculty
│   │   │   ├── subjects/page.tsx     # manage subjects
│   │   │   ├── students/page.tsx     # manage students
│   │   │   ├── assignments/page.tsx  # assign faculty to subjects
│   │   │   └── reports/page.tsx      # department-wide attainment reports
│   │   │
│   │   ├── (faculty)/
│   │   │   ├── dashboard/page.tsx
│   │   │   ├── subjects/[id]/marks/page.tsx  # mark entry grid
│   │   │   └── reports/page.tsx      # subject-wise attainment report
│   │   │
│   │   ├── layout.tsx
│   │   └── middleware.ts             # route guards by role
│   │
│   ├── components/
│   │   ├── ui/                       # shadcn/ui primitives (button, table, dialog...)
│   │   ├── marks/
│   │   │   ├── MarksEntryTable.tsx
│   │   │   └── MarksEntryForm.tsx
│   │   ├── reports/
│   │   │   ├── AttainmentChart.tsx
│   │   │   └── AttainmentTable.tsx
│   │   └── shared/
│   │       ├── Navbar.tsx
│   │       └── RoleGuard.tsx
│   │
│   ├── lib/
│   │   ├── api.ts                    # fetch wrapper / axios instance
│   │   ├── auth.ts                   # token storage, session helpers
│   │   └── calculations.ts           # client-side preview calc (optional, mirrors backend)
│   │
│   ├── types/
│   │   ├── user.ts
│   │   ├── subject.ts
│   │   ├── student.ts
│   │   └── marks.ts
│   │
│   ├── public/
│   ├── tailwind.config.ts
│   ├── next.config.js
│   ├── package.json
│   └── .env.local
│
├── docs/
│   ├── er-diagram.mermaid
│   └── architecture.mermaid
│
└── README.md
```
