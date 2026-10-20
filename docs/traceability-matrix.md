# Traceability Matrix

| Excel Field | DB Column | API Field | UI Component/Page | Report Output |
|---|---|---|---|---|
| Roll Number | `students.roll_num` | `StudentCreate.roll_num` | `frontend/app/(admin)/students/page.tsx` | Student identity columns |
| Register Number | `students.register_num` | `StudentCreate.register_num` | `frontend/app/(admin)/students/page.tsx` | Student identity columns |
| Student Name | `students.name` | `StudentCreate.name` | `frontend/app/(admin)/students/page.tsx` | Student identity columns |
| CIA CO1..CO5 | `student_marks.cia_co1..cia_co5` | `MarksUpsert.cia_co1..cia_co5` | `frontend/components/marks/MarksEntryForm.tsx` | CO-wise marks section |
| Assignment CO1..CO5 | `student_marks.assess_co1..assess_co5` | `MarksUpsert.assess_co1..assess_co5` | `frontend/components/marks/MarksEntryForm.tsx` | CO-wise marks section |
| Presentation | `student_marks.presentation` | `MarksUpsert.presentation` | `frontend/components/marks/MarksEntryForm.tsx` | Internal computation base |
| Quiz | `student_marks.quiz` | `MarksUpsert.quiz` | `frontend/components/marks/MarksEntryForm.tsx` | Internal computation base |
| EndSem CO1..CO5 | `student_marks.endsem_co1..endsem_co5` | `MarksUpsert.endsem_co1..endsem_co5` | `frontend/components/marks/MarksEntryForm.tsx` | EndSem section |
| Internal X CO1..CO5 | `student_marks.internal_x_co1..co5` | `MarkRead.internal_x` | `frontend/components/reports/AttainmentTable.tsx` | Direct attainment report |
| EndSem Y CO1..CO5 | `student_marks.endsem_y_co1..co5` | `MarkRead.endsem_y` | `frontend/components/reports/AttainmentTable.tsx` | Direct attainment report |
| Direct Attainment CO1..CO5 | `student_marks.direct_attainment_co1..co5` | `MarkRead.direct_attainment` | `frontend/components/reports/AttainmentTable.tsx` | CO direct/final attainment |
