"""
test_marks.py — Integration tests for the /marks endpoints.

Verifies:
  - Faculty can only upsert marks for their assigned subjects.
  - Calculation engine results are stored correctly on upsert.
  - Re-upsert updates the record rather than creating a duplicate.
  - Admins can upsert/delete marks for any subject.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.faculty_subject_assignment import FacultySubjectAssignment
from app.models.student import Student
from app.models.subject import Subject


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name='student')
def student_fixture(db: Session) -> Student:
    st = Student(
        roll_num='R001',
        register_num='REG001',
        name='Alice',
        department='CSE',
        semester=1,
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    return st


def _marks_payload(student_id: int, subject_id: int) -> dict:
    return {
        'student_id': student_id,
        'subject_id': subject_id,
        'cia_co1': 30, 'cia_co2': 28, 'cia_co3': 32, 'cia_co4': 25, 'cia_co5': 35,
        'assess_co1': 8, 'assess_co2': 7, 'assess_co3': 9, 'assess_co4': 6, 'assess_co5': 10,
        'presentation': 75,
        'quiz': 80,
        'endsem_co1': 15, 'endsem_co2': 14, 'endsem_co3': 16, 'endsem_co4': 13, 'endsem_co5': 18,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMarksUpsert:
    def test_faculty_can_upsert_assigned_subject(
        self,
        client: TestClient,
        faculty_token: str,
        faculty_assignment: FacultySubjectAssignment,
        student: Student,
        subject: Subject,
    ):
        resp = client.post(
            '/api/v1/marks/upsert',
            json=_marks_payload(student.id, subject.id),
            headers={'Authorization': f'Bearer {faculty_token}'},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Derived fields should be computed
        assert 'internal_x_co1' in data
        assert 'direct_attainment_co1' in data
        # Sanity check: internal_x_co1 = ((30*2.5)+(8*10)+75+80)/400*100 = 77.5
        assert data['internal_x_co1'] == pytest.approx(77.5)
        # endsem_y_co1 = (15/20)*100 = 75
        assert data['endsem_y_co1'] == pytest.approx(75.0)
        # direct_att_co1 = 77.5*0.4 + 75*0.6 = 31 + 45 = 76
        assert data['direct_attainment_co1'] == pytest.approx(76.0)

    def test_upsert_updates_existing_record(
        self,
        client: TestClient,
        faculty_token: str,
        faculty_assignment: FacultySubjectAssignment,
        student: Student,
        subject: Subject,
    ):
        payload = _marks_payload(student.id, subject.id)
        # First insert
        resp1 = client.post(
            '/api/v1/marks/upsert',
            json=payload,
            headers={'Authorization': f'Bearer {faculty_token}'},
        )
        assert resp1.status_code == 200
        id1 = resp1.json()['id']

        # Update cia_co1 to 40 (full marks)
        payload['cia_co1'] = 40
        resp2 = client.post(
            '/api/v1/marks/upsert',
            json=payload,
            headers={'Authorization': f'Bearer {faculty_token}'},
        )
        assert resp2.status_code == 200
        id2 = resp2.json()['id']

        # Same record updated, not a new insert
        assert id1 == id2
        # internal_x_co1 with cia=40: ((40*2.5)+(8*10)+75+80)/400*100 = (100+80+75+80)/400*100 = 83.75
        assert resp2.json()['internal_x_co1'] == pytest.approx(83.75)

    def test_faculty_cannot_upsert_unassigned_subject(
        self,
        client: TestClient,
        faculty_token: str,
        student: Student,
        subject: Subject,
        # Note: no faculty_assignment fixture — faculty is NOT assigned
    ):
        resp = client.post(
            '/api/v1/marks/upsert',
            json=_marks_payload(student.id, subject.id),
            headers={'Authorization': f'Bearer {faculty_token}'},
        )
        assert resp.status_code == 403

    def test_admin_can_upsert_any_subject(
        self,
        client: TestClient,
        admin_token: str,
        student: Student,
        subject: Subject,
        # No assignment needed for admin
    ):
        resp = client.post(
            '/api/v1/marks/upsert',
            json=_marks_payload(student.id, subject.id),
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200

    def test_upsert_nonexistent_student(
        self,
        client: TestClient,
        admin_token: str,
        subject: Subject,
    ):
        resp = client.post(
            '/api/v1/marks/upsert',
            json=_marks_payload(99999, subject.id),
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 404


class TestMarksList:
    def test_list_returns_marks(
        self,
        client: TestClient,
        faculty_token: str,
        faculty_assignment: FacultySubjectAssignment,
        student: Student,
        subject: Subject,
    ):
        # Seed a record
        client.post(
            '/api/v1/marks/upsert',
            json=_marks_payload(student.id, subject.id),
            headers={'Authorization': f'Bearer {faculty_token}'},
        )
        resp = client.get(
            '/api/v1/marks/',
            headers={'Authorization': f'Bearer {faculty_token}'},
        )
        assert resp.status_code == 200
        records = resp.json()
        assert len(records) >= 1
