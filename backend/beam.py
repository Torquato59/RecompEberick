"""Viga Euler–Bernoulli com apoios ideais e EI constante.

Unidades: m, kN, kN/m². Flecha/cargas positivas para baixo, reações verticais
para cima, momento interno positivo sagente e reações de momento anti-horárias.
Solução analítica por integração e quatro condições de contorno; sem malha.
"""

from dataclasses import dataclass
import math
from typing import Any


class ValidationError(ValueError):
    pass


FIELDS = {
    "span_m": (0.1, 100.0, "Comprimento (m)"),
    "elastic_modulus_gpa": (0.1, 1000.0, "Módulo de elasticidade (GPa)"),
    "width_m": (0.01, 10.0, "Largura (m)"),
    "height_m": (0.01, 10.0, "Altura (m)"),
    "uniform_load_kn_m": (0.0, 1_000_000.0, "Carga distribuída (kN/m)"),
    "point_load_kn": (0.0, 1_000_000.0, "Carga pontual (kN)"),
    "point_position_m": (0.0, 100.0, "Posição da carga pontual (m)"),
}
SUPPORTS = {"pinned", "roller", "fixed", "free"}


@dataclass(frozen=True)
class BeamInput:
    span_m: float
    elastic_modulus_gpa: float
    width_m: float
    height_m: float
    uniform_load_kn_m: float
    point_load_kn: float
    point_position_m: float
    support_left: str = "pinned"
    support_right: str = "roller"

    @classmethod
    def from_dict(cls, data: Any) -> "BeamInput":
        if not isinstance(data, dict):
            raise ValidationError("Informe um objeto com os dados da viga.")
        if set(data) - set(FIELDS) - {"support_left", "support_right"}:
            raise ValidationError("O projeto contém campos desconhecidos.")
        values = {}
        for name, (low, high, label) in FIELDS.items():
            value = data.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValidationError(f"{label}: informe um número.")
            try:
                value = float(value)
            except (OverflowError, ValueError):
                raise ValidationError(f"{label}: valor fora do intervalo permitido.") from None
            if not math.isfinite(value) or not low <= value <= high:
                raise ValidationError(f"{label}: use um valor entre {low:g} e {high:g}.")
            values[name] = value
        if values["point_position_m"] > values["span_m"]:
            raise ValidationError("A carga pontual deve estar dentro do comprimento da viga (0 ≤ posição ≤ L).")
        for name, default in [("support_left", "pinned"), ("support_right", "roller")]:
            value = data.get(name, default)
            if not isinstance(value, str) or value not in SUPPORTS:
                raise ValidationError("Tipo de apoio inválido. Escolha articulado, móvel, engastado ou livre.")
            values[name] = value
        left, right = values["support_left"], values["support_right"]
        if "fixed" not in (left, right):
            if "free" in (left, right):
                raise ValidationError("Combinação instável: uma extremidade livre exige um engaste na outra extremidade.")
            if left == right == "roller":
                raise ValidationError("Combinação instável: dois apoios móveis não restringem a translação horizontal. Use um articulado ou engaste.")
        return cls(**values)


def solve_four(matrix, force):
    """Eliminação com pivoteamento; incógnitas normalizadas em unidades de momento."""
    augmented = [list(row) + [rhs] for row, rhs in zip(matrix, force)]
    for col in range(4):
        pivot = max(range(col, 4), key=lambda row: abs(augmented[row][col]))
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        divisor = augmented[col][col]
        if abs(divisor) < 1e-14:
            raise ValidationError("As condições de apoio não definem uma viga estável.")
        augmented[col] = [value / divisor for value in augmented[col]]
        for row in range(4):
            if row != col:
                factor = augmented[row][col]
                augmented[row] = [a - factor * b for a, b in zip(augmented[row], augmented[col])]
    return [row[-1] for row in augmented]


def polynomial_roots(coefficients, low, high):
    """Todas as raízes reais no intervalo, isoladas pelos extremos da derivada.

    Grau máximo três. Normalizar x/L evita coeficientes mal escalados. A
    partição em trechos monótonos permite localizar também raízes tangentes.
    """
    coefficients = list(coefficients)
    while len(coefficients) > 1 and coefficients[-1] == 0:
        coefficients.pop()
    if len(coefficients) == 1 or high <= low:
        return []
    def evaluate(x):
        value = 0.0
        for coefficient in reversed(coefficients):
            value = value * x + coefficient
        return value
    if len(coefficients) == 2:
        root = -coefficients[0] / coefficients[1]
        return [root] if low <= root <= high else []
    critical = polynomial_roots([i * c for i, c in enumerate(coefficients)][1:], low, high)
    partitions = sorted(set([low, *critical, high]))
    tolerance = sum(abs(c) for c in coefficients) * 1e-13
    roots = [x for x in partitions if abs(evaluate(x)) <= tolerance]
    for start, end in zip(partitions, partitions[1:]):
        first, last = evaluate(start), evaluate(end)
        if first * last >= 0:
            continue
        for _ in range(80):
            middle = (start + end) / 2
            value = evaluate(middle)
            if first * value <= 0:
                end = middle
            else:
                start, first = middle, value
        roots.append((start + end) / 2)
    return sorted(set(roots))


class Beam:
    def __init__(self, data: BeamInput):
        self.data = data
        self.length, self.q, self.p, self.a = data.span_m, data.uniform_load_kn_m, data.point_load_kn, data.point_position_m
        self.inertia = data.width_m * data.height_m ** 3 / 12
        self.ei = data.elastic_modulus_gpa * 1e6 * self.inertia
        self.alpha = self.a / self.length
        self.Q, self.T = self.q * self.length ** 2, self.p * self.length
        # t=x/L; EI*y/L² = D + C*t - B*t²/2 - R*t³/6 + cargas.
        # B=M(0), R=RA*L. Condições: apoio -> y=M=0;
        # engaste -> y=theta=0; livre -> M=V_externo=0.
        rows, rhs = [], []
        def add(row, value=0.0):
            rows.append(row); rhs.append(value)
        if data.support_left == "fixed":
            add([0, 0, 0, 1]); add([0, 0, 1, 0])
        elif data.support_left == "free":
            add([1, 0, 0, 0]); add([0, 1, 0, 0])
        else:
            add([0, 0, 0, 1]); add([1, 0, 0, 0])
        if data.support_right != "free":
            add([-0.5, -1 / 6, 1, 1], -self.Q / 24 - self.T * (1 - self.alpha) ** 3 / 6)
        else:
            add([0, 1, 0, 0], self.Q + self.T)
        if data.support_right == "fixed":
            add([-1, -0.5, 1, 0], -self.Q / 6 - self.T * (1 - self.alpha) ** 2 / 2)
        else:
            add([1, 1, 0, 0], self.Q / 2 + self.T * (1 - self.alpha))
        self.B, self.R, self.C, self.D = solve_four(rows, rhs)
        self.left_reaction = 0.0 if data.support_left == "free" else self.R / self.length
        self.right_reaction = 0.0 if data.support_right == "free" else self.q * self.length + self.p - self.left_reaction
        self.left_moment = -self.B if data.support_left == "fixed" else 0.0
        self.right_moment = self.moment(self.length) if data.support_right == "fixed" else 0.0

    def shear(self, x: float, side: str = "right") -> float:
        applied = x > self.a or (x == self.a and side == "right")
        return self.left_reaction - self.q * x - (self.p if applied else 0)

    def moment(self, x: float) -> float:
        if (x == 0 and self.data.support_left != "fixed") or (x == self.length and self.data.support_right != "fixed"):
            return 0.0
        t = x / self.length
        return self.B + self.R * t - self.Q * t ** 2 / 2 - self.T * max(t - self.alpha, 0)

    def deflection(self, x: float) -> float:
        if (x == 0 and self.data.support_left != "free") or (x == self.length and self.data.support_right != "free"):
            return 0.0
        t = x / self.length
        return (self.D + self.C * t - self.B * t ** 2 / 2 - self.R * t ** 3 / 6 + self.Q * t ** 4 / 24 + self.T * max(t - self.alpha, 0) ** 3 / 6) * self.length ** 2 / self.ei

    def slope(self, x: float) -> float:
        if (x == 0 and self.data.support_left == "fixed") or (x == self.length and self.data.support_right == "fixed"):
            return 0.0
        t = x / self.length
        return (self.C - self.B * t - self.R * t ** 2 / 2 + self.Q * t ** 3 / 6 + self.T * max(t - self.alpha, 0) ** 2 / 2) * self.length / self.ei

    def result(self) -> dict:
        moment_candidates = {0.0, self.a, self.length}
        if self.Q:
            for t, low, high in [(self.R / self.Q, 0, self.alpha), ((self.R - self.T) / self.Q, self.alpha, 1)]:
                if low <= t <= high:
                    moment_candidates.add(t * self.length)
        moment_x = max(sorted(moment_candidates), key=lambda x: abs(self.moment(x)))
        positive_x = max(sorted(moment_candidates), key=self.moment)
        negative_x = min(sorted(moment_candidates), key=self.moment)
        deflection_candidates = {0.0, self.a, self.length}
        for coefficients, low, high in [
            ([self.C, -self.B, -self.R / 2, self.Q / 6], 0, self.alpha),
            ([self.C + self.T * self.alpha ** 2 / 2, -self.B - self.T * self.alpha, (-self.R + self.T) / 2, self.Q / 6], self.alpha, 1),
        ]:
            deflection_candidates.update(t * self.length for t in polynomial_roots(coefficients, low, high))
        deflection_x = max(sorted(deflection_candidates), key=lambda x: abs(self.deflection(x)))
        positions = {self.length * i / 200 for i in range(201)} | moment_candidates | deflection_candidates
        samples = []
        for x in sorted(positions):
            sides = ["left", "right"] if self.p and x == self.a and 0 < x < self.length else ["left" if x == self.length else "right"]
            for side in sides:
                samples.append({"x_m": x, "side": side, "shear_kn": self.shear(x, side), "moment_kn_m": self.moment(x), "deflection_mm": self.deflection(x) * 1000, "rotation_mrad": self.slope(x) * 1000})
        maximum_shear = max(abs(s["shear_kn"]) for s in samples)
        signed_moment = self.moment(moment_x)
        maximum_moment = abs(signed_moment)
        area = self.data.width_m * self.data.height_m
        modulus = self.inertia / (self.data.height_m / 2)
        types = (self.data.support_left, self.data.support_right)
        beam_type = "Viga em balanço" if "free" in types else "Viga biengastada" if types == ("fixed", "fixed") else "Viga engastada e apoiada" if "fixed" in types else "Viga biapoiada"
        return {
            "method": "Euler–Bernoulli · integração analítica e condições de contorno · EI constante",
            "beam_type": beam_type,
            "supports": {"left": types[0], "right": types[1]},
            "integration_constants": {"initial_moment_kn_m": self.B, "c_kn_m2": self.C * self.length, "d_kn_m3": self.D * self.length ** 2},
            "inertia_m4": self.inertia,
            "flexural_rigidity_kn_m2": self.ei,
            "section": {"area_m2": area, "section_modulus_m3": modulus},
            "elastic_results": {"total_load_kn": self.q * self.length + self.p, "max_bending_stress_mpa": maximum_moment / modulus / 1000, "max_shear_stress_mpa": 1.5 * maximum_shear / area / 1000, "left_rotation_mrad": self.slope(0) * 1000, "right_rotation_mrad": self.slope(self.length) * 1000},
            "reactions": {"left_kn": self.left_reaction, "right_kn": self.right_reaction, "left_moment_kn_m": self.left_moment, "right_moment_kn_m": self.right_moment},
            "extrema": {"moment_kn_m": maximum_moment, "signed_moment_kn_m": signed_moment, "moment_position_m": moment_x, "positive_moment_kn_m": max(0.0, self.moment(positive_x)), "negative_moment_kn_m": min(0.0, self.moment(negative_x)), "deflection_mm": abs(self.deflection(deflection_x)) * 1000, "signed_deflection_mm": self.deflection(deflection_x) * 1000, "deflection_position_m": deflection_x, "absolute_shear_kn": maximum_shear},
            "equilibrium": {"force_residual_kn": self.left_reaction + self.right_reaction - self.q * self.length - self.p, "moment_residual_kn_m": self.left_moment + self.right_moment + self.right_reaction * self.length - self.q * self.length ** 2 / 2 - self.p * self.a},
            "samples": samples,
        }


def calculate(data: Any) -> dict:
    return Beam(BeamInput.from_dict(data)).result()
