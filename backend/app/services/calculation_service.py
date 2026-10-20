"""
calculation_service.py — CO Attainment Calculation Engine.

Implements the formulas reverse-engineered from the sample Excel workbook
(`CO_ATT_INPUTS` sheet), frozen in docs/excel-data-dictionary.md.

For each CO index i ∈ {1, 2, 3, 4, 5}:

    internal_x_i  = ((cia_co_i * 2.5) + (assess_co_i * 10)
                      + presentation + quiz) / 400 * 100

    endsem_y_i    = (endsem_co_i / 20) * 100

    direct_att_i  = (internal_x_i * 0.4) + (endsem_y_i * 0.6)

Results are stored with full float precision; display rounding (2 d.p.)
is the responsibility of the reporting / export layer.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class _InputMarks:
    """Value-object carrying one student-subject mark record."""

    cia_co1: float
    cia_co2: float
    cia_co3: float
    cia_co4: float
    cia_co5: float

    assess_co1: float
    assess_co2: float
    assess_co3: float
    assess_co4: float
    assess_co5: float

    presentation: float
    quiz: float

    endsem_co1: float
    endsem_co2: float
    endsem_co3: float
    endsem_co4: float
    endsem_co5: float


@dataclass(frozen=True)
class AttainmentResult:
    """Computed CO attainment values for a single student-subject record."""

    internal_x_co1: float
    internal_x_co2: float
    internal_x_co3: float
    internal_x_co4: float
    internal_x_co5: float

    endsem_y_co1: float
    endsem_y_co2: float
    endsem_y_co3: float
    endsem_y_co4: float
    endsem_y_co5: float

    direct_attainment_co1: float
    direct_attainment_co2: float
    direct_attainment_co3: float
    direct_attainment_co4: float
    direct_attainment_co5: float


# ---------------------------------------------------------------------------
# Pure calculation helpers
# ---------------------------------------------------------------------------


def _compute_internal_x(
    cia: float,
    assess: float,
    presentation: float,
    quiz: float,
) -> float:
    """Internal percentage for one CO.

    Formula: ((CIA*2.5 + Assignment*10 + Presentation + Quiz) / 400) * 100
    """
    numerator = (cia * 2.5) + (assess * 10) + presentation + quiz
    return (numerator / 400.0) * 100.0


def _compute_endsem_y(endsem: float) -> float:
    """End-semester percentage for one CO.

    Formula: (EndSemCO / 20) * 100
    """
    return (endsem / 20.0) * 100.0


def _compute_direct_attainment(internal_x: float, endsem_y: float) -> float:
    """Direct attainment for one CO.

    Formula: (Internal_X * 0.4) + (EndSem_Y * 0.6)
    """
    return (internal_x * 0.4) + (endsem_y * 0.6)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def calculate_attainment(
    cia_co1: float,
    cia_co2: float,
    cia_co3: float,
    cia_co4: float,
    cia_co5: float,
    assess_co1: float,
    assess_co2: float,
    assess_co3: float,
    assess_co4: float,
    assess_co5: float,
    presentation: float,
    quiz: float,
    endsem_co1: float,
    endsem_co2: float,
    endsem_co3: float,
    endsem_co4: float,
    endsem_co5: float,
) -> AttainmentResult:
    """Compute all derived CO attainment metrics from raw mark inputs.

    Args:
        cia_co1..5    : CIA marks per CO (each out of 40).
        assess_co1..5 : Assignment marks per CO (each out of 10).
        presentation  : Presentation / Tutorial mark (out of 100).
        quiz          : Quiz mark (out of 100).
        endsem_co1..5 : End-semester marks per CO (each out of 20).

    Returns:
        AttainmentResult with internal_x, endsem_y, and direct_attainment
        for each of the 5 Course Outcomes.
    """
    marks = _InputMarks(
        cia_co1=cia_co1,
        cia_co2=cia_co2,
        cia_co3=cia_co3,
        cia_co4=cia_co4,
        cia_co5=cia_co5,
        assess_co1=assess_co1,
        assess_co2=assess_co2,
        assess_co3=assess_co3,
        assess_co4=assess_co4,
        assess_co5=assess_co5,
        presentation=presentation,
        quiz=quiz,
        endsem_co1=endsem_co1,
        endsem_co2=endsem_co2,
        endsem_co3=endsem_co3,
        endsem_co4=endsem_co4,
        endsem_co5=endsem_co5,
    )

    # Internal X per CO
    ix = [
        _compute_internal_x(
            getattr(marks, f'cia_co{i}'),
            getattr(marks, f'assess_co{i}'),
            marks.presentation,
            marks.quiz,
        )
        for i in range(1, 6)
    ]

    # EndSem Y per CO
    ey = [_compute_endsem_y(getattr(marks, f'endsem_co{i}')) for i in range(1, 6)]

    # Direct Attainment per CO
    da = [_compute_direct_attainment(ix[i], ey[i]) for i in range(5)]

    return AttainmentResult(
        internal_x_co1=ix[0],
        internal_x_co2=ix[1],
        internal_x_co3=ix[2],
        internal_x_co4=ix[3],
        internal_x_co5=ix[4],
        endsem_y_co1=ey[0],
        endsem_y_co2=ey[1],
        endsem_y_co3=ey[2],
        endsem_y_co4=ey[3],
        endsem_y_co5=ey[4],
        direct_attainment_co1=da[0],
        direct_attainment_co2=da[1],
        direct_attainment_co3=da[2],
        direct_attainment_co4=da[3],
        direct_attainment_co5=da[4],
    )


def apply_attainment_to_marks_row(marks_row: object, result: AttainmentResult) -> None:
    """Write calculated fields back onto a StudentMarks ORM instance in-place.

    Args:
        marks_row : A StudentMarks SQLModel instance.
        result    : The AttainmentResult returned by calculate_attainment().
    """
    for co in range(1, 6):
        setattr(marks_row, f'internal_x_co{co}', getattr(result, f'internal_x_co{co}'))
        setattr(marks_row, f'endsem_y_co{co}', getattr(result, f'endsem_y_co{co}'))
        setattr(
            marks_row,
            f'direct_attainment_co{co}',
            getattr(result, f'direct_attainment_co{co}'),
        )
