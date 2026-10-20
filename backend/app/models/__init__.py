from app.models.faculty_subject_assignment import FacultySubjectAssignment
from app.models.student import Student
from app.models.student_marks import StudentMarks
from app.models.subject import Subject
from app.models.user import User, UserRole

__all__ = [
    'User',
    'UserRole',
    'Subject',
    'Student',
    'FacultySubjectAssignment',
    'StudentMarks',
]
