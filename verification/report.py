"""Compara duas implementações distintas do mesmo modelo físico elástico."""

from functools import lru_cache

from backend.beam import calculate
from .cases import CASES
from .fem import solve

RELATIVE_TOLERANCE = 3e-6
ABSOLUTE_TOLERANCE = 1e-8  # Nas unidades de cada grandeza retornada.


@lru_cache(maxsize=1)
def run_validation():
    cases = []
    for key, label, model in CASES:
        analytical = calculate(model)
        reference = solve(model)
        values = analytical["reactions"] | analytical["extrema"] | analytical["elastic_results"]
        checks = []
        for name in ["left_kn", "right_kn", "moment_kn_m", "deflection_mm", "absolute_shear_kn", "left_rotation_mrad", "right_rotation_mrad", "max_bending_stress_mpa", "max_shear_stress_mpa"]:
            actual, expected = values[name], reference[name]
            error = abs(actual - expected)
            tolerance = ABSOLUTE_TOLERANCE + RELATIVE_TOLERANCE * abs(expected)
            checks.append({"quantity": name, "analytical": actual, "reference": expected, "absolute_error": error, "relative_error": error / abs(expected) if abs(expected) > ABSOLUTE_TOLERANCE else None, "tolerance": tolerance, "passed": error <= tolerance})
        cases.append({
            "id": key, "label": label, "model": model, "elements": reference["elements"],
            "checks": checks, "passed": all(check["passed"] for check in checks),
        })
    return {
        "method": "Elementos finitos de Euler–Bernoulli; rigidez, forças consistentes e interpolação de Hermite",
        "relative_tolerance": RELATIVE_TOLERANCE,
        "absolute_tolerance": ABSOLUTE_TOLERANCE,
        "cases": cases,
        "passed_cases": sum(case["passed"] for case in cases),
        "total_cases": len(cases),
        "passed_checks": sum(check["passed"] for case in cases for check in case["checks"]),
        "total_checks": sum(len(case["checks"]) for case in cases),
        "passed": all(case["passed"] for case in cases),
    }
