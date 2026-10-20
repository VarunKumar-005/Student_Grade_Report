"""test_role_hierarchy.py — Integration tests for institutional role hierarchy.

Tests the four tiers:
  SUPER_ADMIN  -> manages Departments and HODs, institution-wide views
  HOD          -> manages their department's Faculty, Sections, Subjects, and Enrollments
  FACULTY      -> manages assigned Sections and marks entry
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.department import Department
from app.models.section import Section
from app.models.subject import Subject
from app.models.user import User, UserRole


def test_super_admin_can_create_department_and_assign_hod(
    client: TestClient,
    super_admin_token: str,
    db: Session,
):
    # 1. SuperAdmin creates a department
    dept_resp = client.post(
        '/api/v1/departments/',
        json={'name': 'Electrical and Electronics Engineering', 'code': 'EEE'},
        headers={'Authorization': f'Bearer {super_admin_token}'},
    )
    assert dept_resp.status_code == 201
    dept_data = dept_resp.json()
    assert dept_data['code'] == 'EEE'
    dept_id = dept_data['id']

    # 2. SuperAdmin creates a user to become HOD
    user_resp = client.post(
        '/api/v1/users/',
        json={
            'name': 'Dr. Suresh',
            'email': 'suresh@eee.college.edu',
            'password': 'SureshPassword123!',
            'role': 'HOD',
            'department_id': dept_id,
        },
        headers={'Authorization': f'Bearer {super_admin_token}'},
    )
    assert user_resp.status_code == 201
    hod_user_id = user_resp.json()['id']

    # 3. SuperAdmin assigns HOD to department
    assign_resp = client.put(
        f'/api/v1/departments/{dept_id}/hod',
        json={'user_id': hod_user_id},
        headers={'Authorization': f'Bearer {super_admin_token}'},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()['hod_id'] == hod_user_id


def test_hod_can_create_faculty_and_section_for_own_dept(
    client: TestClient,
    hod_token: str,
    department: Department,
):
    # 1. HOD creates a Faculty in their department
    fac_resp = client.post(
        '/api/v1/users/',
        json={
            'name': 'Prof. Anitha',
            'email': 'anitha@cse.college.edu',
            'password': 'AnithaPassword123!',
            'role': 'FACULTY',
        },
        headers={'Authorization': f'Bearer {hod_token}'},
    )
    assert fac_resp.status_code == 201
    fac_data = fac_resp.json()
    assert fac_data['department_id'] == department.id
    assert fac_data['role'] == 'FACULTY'

    # 2. HOD cannot create another HOD or SuperAdmin
    forbidden_resp = client.post(
        '/api/v1/users/',
        json={
            'name': 'Rogue Admin',
            'email': 'rogue@college.edu',
            'password': 'RoguePassword123!',
            'role': 'SUPER_ADMIN',
        },
        headers={'Authorization': f'Bearer {hod_token}'},
    )
    assert forbidden_resp.status_code == 403

    # 3. HOD creates a section in their own department
    sec_resp = client.post(
        '/api/v1/sections/',
        json={
            'name': 'CSE-B',
            'department_id': department.id,
            'semester': 4,
            'academic_year': '2025-26',
        },
        headers={'Authorization': f'Bearer {hod_token}'},
    )
    assert sec_resp.status_code == 201
    assert sec_resp.json()['name'] == 'CSE-B'


def test_faculty_enroll_student_in_assigned_section(
    client: TestClient,
    faculty_token: str,
    faculty_assignment,
    section: Section,
):
    # Faculty enrolls a student into their assigned section
    enroll_resp = client.post(
        f'/api/v1/sections/{section.id}/students',
        json={
            'roll_num': 'CSE2025099',
            'register_num': 'REG99999',
            'name': 'Kavya Raman',
            'semester': 3,
        },
        headers={'Authorization': f'Bearer {faculty_token}'},
    )
    assert enroll_resp.status_code == 201
    assert enroll_resp.json()['student_roll'] == 'CSE2025099'
    assert enroll_resp.json()['student_name'] == 'Kavya Raman'

    # Verify listing enrolled students
    list_resp = client.get(
        f'/api/v1/sections/{section.id}/students',
        headers={'Authorization': f'Bearer {faculty_token}'},
    )
    assert list_resp.status_code == 200
    rolls = [s['student_roll'] for s in list_resp.json()]
    assert 'CSE2025099' in rolls


def test_hod_bulk_enroll_students_in_section(
    client: TestClient,
    hod_token: str,
    section: Section,
):
    bulk_payload = {
        'students': [
            {'roll_num': 'CSE2025101', 'register_num': 'REG101', 'name': 'Devi P', 'semester': 3},
            {'roll_num': 'CSE2025102', 'register_num': 'REG102', 'name': 'Ganesh K', 'semester': 3},
        ]
    }
    resp = client.post(
        f'/api/v1/sections/{section.id}/students/bulk',
        json=bulk_payload,
        headers={'Authorization': f'Bearer {hod_token}'},
    )
    assert resp.status_code == 201
    assert len(resp.json()) == 2


def test_hod_cannot_create_or_view_other_department_sections(
    client: TestClient,
    hod_token: str,
    super_admin_token: str,
):
    # 1. SuperAdmin creates a distinct Mechanical department
    mech_dept = client.post(
        '/api/v1/departments/',
        json={'name': 'Mechanical Engineering', 'code': 'MECH'},
        headers={'Authorization': f'Bearer {super_admin_token}'},
    ).json()

    # 2. HOD of CSE tries to create a section for Mechanical -> 403 Forbidden
    resp = client.post(
        '/api/v1/sections/',
        json={
            'name': 'MECH-A',
            'department_id': mech_dept['id'],
            'semester': 3,
            'academic_year': '2025-26',
        },
        headers={'Authorization': f'Bearer {hod_token}'},
    )
    assert resp.status_code == 403


def test_reports_access_and_scoping(
    client: TestClient,
    super_admin_token: str,
    hod_token: str,
    department: Department,
):
    # SuperAdmin can view attainment report
    sa_rep = client.get(
        '/api/v1/reports/attainment',
        headers={'Authorization': f'Bearer {super_admin_token}'},
    )
    assert sa_rep.status_code == 200

    # HOD can view attainment report for own department
    hod_rep = client.get(
        f'/api/v1/reports/attainment?department_id={department.id}',
        headers={'Authorization': f'Bearer {hod_token}'},
    )
    assert hod_rep.status_code == 200
