# Excel Data Dictionary (`sample_attainment_sheet.xlsx`)

Workbook sheets discovered:
1. `PO_AND_PSO`
2. `CO_PO MAPPING_PRINT`
3. `CO_ATT_INPUTS`
4. `CO DIRECT ATT`
5. `CO INDIRECT ATT`
6. `CO ATT`
7. `FOR SESSION PURPOSE`

## Canonical operational sheet: `CO_ATT_INPUTS`

### Student identity fields
| Excel Column | Header | Type | Classification | Backend target |
|---|---|---|---|---|
| A | S. No | integer | Input | transient row index |
| B | ROLL NUM | string | Input | `students.roll_num` |
| C | REGISTER NUMBER | string | Input | `students.register_num` |
| D | NAME OF THE STUDENT | string | Input | `students.name` |

### Mark entry fields (inputs)
| Excel Columns | Header Group | Value Range in sheet | Classification | Backend target |
|---|---|---|---|---|
| E-I | CIA CO1..CO5 | out of 40 each | Input | `student_marks.cia_co1..cia_co5` |
| J-N | Assignment CO1..CO5 | out of 10 each | Input | `student_marks.assess_co1..assess_co5` |
| O | Presentation / Tutorial | out of 100 | Input | `student_marks.presentation` |
| P | Quiz | out of 100 | Input | `student_marks.quiz` |
| Q-U | End Semester CO1..CO5 | out of 20 each | Input | `student_marks.endsem_co1..endsem_co5` |

### Derived metrics (sheet formulas)
| Excel Columns | Header Group | Formula | Classification | Backend target |
|---|---|---|---|---|
| V-Z | Internal X for CO1..CO5 | `((((CIA*2.5)+(Assignment*10)+Presentation+Quiz)/400)*100)` | Derived | `internal_x_co1..co5` |
| AA-AE | EndSem Y for CO1..CO5 | `(EndSemCO/20)*100` | Derived | `endsem_y_co1..co5` |
| AF-AJ | Direct Attainment for CO1..CO5 | `(0.4*X + 0.6*Y)` | Derived | `direct_attainment_co1..co5` |

### Threshold and level references
- `CO_ATT_INPUTS!C327 = 70` (target CO assessment threshold used by direct attainment pass/fail flags in dependent sheets).

## Functional calculation requirements (frozen)
For each CO in {1..5}:
1. `internal_x = ((((cia_co * 2.5) + (assess_co * 10) + presentation + quiz) / 400) * 100)`
2. `endsem_y = ((endsem_co / 20) * 100)`
3. `direct_attainment = (internal_x * 0.4) + (endsem_y * 0.6)`

## Rounding policy
- Store and compute using decimal precision.
- Report values rounded to 2 decimal places for dashboards/exports.

## Output usage mapping
- `CO DIRECT ATT`: direct attainment per student with threshold checks.
- `CO INDIRECT ATT`: indirect assessment pipeline.
- `CO ATT`: weighted final attainment composition.
- `FOR SESSION PURPOSE`: consolidated print/report-friendly projection.
