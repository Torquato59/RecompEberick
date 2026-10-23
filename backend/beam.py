"""Viga biapoiada de Euler–Bernoulli, EI constante e cargas verticais.

Unidades internas: m, kN, kN/m². Cargas e flecha positivas para baixo;
reações positivas para cima; momento positivo de flexão sagente.
Solução analítica por funções de singularidade, sem discretização de rigidez.
"""

from dataclasses import dataclass
import math
from typing import Any


class ValidationError(ValueError):
    pass


# Limites de entrada do protótipo, não critérios de dimensionamento.
FIELDS = {
    "span_m": (0.1, 100.0, "Vão (m)"),
    "elastic_modulus_gpa": (0.1, 1000.0, "Módulo de elasticidade (GPa)"),
    "width_m": (0.01, 10.0, "Largura (m)"),
    "height_m": (0.01, 10.0, "Altura (m)"),
    "uniform_load_kn_m": (0.0, 1_000_000.0, "Carga distribuída (kN/m)"),
    "point_load_kn": (0.0, 1_000_000.0, "Carga pontual (kN)"),
    "point_position_m": (0.0, 100.0, "Posição da carga pontual (m)"),
}


@dataclass(frozen=True)
class BeamInput:
    span_m: float
    elastic_modulus_gpa: float
    width_m: float
    height_m: float
    uniform_load_kn_m: float
    point_load_kn: float
    point_position_m: float

    @classmethod
    def from_dict(cls, data: Any) -> "BeamInput":
        if not isinstance(data, dict):
            raise ValidationError("Informe um objeto com os dados da viga.")
        if set(data) - set(FIELDS):
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
            raise ValidationError("A carga pontual deve estar entre os apoios (0 ≤ posição ≤ vão).")
        return cls(**values)


class Beam:
    def __init__(self, data: BeamInput):
        self.data = data
        self.length = data.span_m
        self.q = data.uniform_load_kn_m
        self.p = data.point_load_kn
        self.a = data.point_position_m
        self.inertia = data.width_m * data.height_m ** 3 / 12
        self.ei = data.elastic_modulus_gpa * 1e6 * self.inertia
        self.right_reaction = self.q * self.length / 2 + self.p * self.a / self.length
        self.left_reaction = self.q * self.length / 2 + self.p * (self.length - self.a) / self.length
        self.constant = (
            self.left_reaction * self.length ** 3 / 6
            - self.q * self.length ** 4 / 24
            - self.p * (self.length - self.a) ** 3 / 6
        ) / self.length

    def shear(self, x: float, side: str = "right") -> float:
        # Valores imediatamente à esquerda/direita de uma carga, dentro do vão.
        applied = x > self.a or (x == self.a and side == "right")
        return self.left_reaction - self.q * x - (self.p if applied else 0)

    def moment(self, x: float) -> float:
        if x == 0 or x == self.length:
            return 0.0
        return self.left_reaction * x - self.q * x ** 2 / 2 - self.p * max(x - self.a, 0)

    def deflection(self, x: float) -> float:
        if x == 0 or x == self.length:
            return 0.0
        return (
            self.constant * x - self.left_reaction * x ** 3 / 6
            + self.q * x ** 4 / 24 + self.p * max(x - self.a, 0) ** 3 / 6
        ) / self.ei

    def slope(self, x: float) -> float:
        return (
            self.constant - self.left_reaction * x ** 2 / 2
            + self.q * x ** 3 / 6 + self.p * max(x - self.a, 0) ** 2 / 2
        ) / self.ei

    def result(self) -> dict:
        # Extremos de M em V=0, na carga pontual ou nas extremidades.
        candidates = {0.0, self.a, self.length}
        if self.q:
            for x, low, high in (
                (self.left_reaction / self.q, 0.0, self.a),
                ((self.left_reaction - self.p) / self.q, self.a, self.length),
            ):
                if low <= x <= high:
                    candidates.add(x)
        moment_x = max(candidates, key=self.moment)
        # Para cargas não negativas, y''=-M/EI <= 0: y' é monótona.
        has_bending = self.q > 0 or (self.p > 0 and 0 < self.a < self.length)
        if has_bending:
            low, high = 0.0, self.length
            for _ in range(80):
                midpoint = (low + high) / 2
                if self.slope(midpoint) > 0:
                    low = midpoint
                else:
                    high = midpoint
            deflection_x = (low + high) / 2
        else:
            deflection_x = 0.0
        # Duas amostras na posição da carga preservam o salto de cortante.
        positions = {self.length * i / 200 for i in range(201)}
        positions.update((self.a, moment_x, deflection_x))
        samples = []
        for x in sorted(positions):
            sides = ["left", "right"] if self.p and x == self.a and 0 < x < self.length else [
                "left" if x == self.length else "right"
            ]
            for side in sides:
                samples.append({
                    "x_m": x,
                    "side": side,
                    "shear_kn": self.shear(x, side),
                    "moment_kn_m": self.moment(x),
                    "deflection_mm": self.deflection(x) * 1000,
                    "rotation_mrad": self.slope(x) * 1000,
                })
        maximum_shear = max(abs(s["shear_kn"]) for s in samples)
        maximum_moment = max(0.0, self.moment(moment_x))
        area = self.data.width_m * self.data.height_m
        section_modulus = self.inertia / (self.data.height_m / 2)
        return {
            "method": "Euler–Bernoulli · solução analítica · EI constante",
            "inertia_m4": self.inertia,
            "flexural_rigidity_kn_m2": self.ei,
            "section": {"area_m2": area, "section_modulus_m3": section_modulus},
            "elastic_results": {
                "total_load_kn": self.q * self.length + self.p,
                "max_bending_stress_mpa": maximum_moment / section_modulus / 1000,
                "max_shear_stress_mpa": 1.5 * maximum_shear / area / 1000,
                "left_rotation_mrad": self.slope(0) * 1000,
                "right_rotation_mrad": self.slope(self.length) * 1000,
            },
            "reactions": {"left_kn": self.left_reaction, "right_kn": self.right_reaction},
            "extrema": {
                "moment_kn_m": maximum_moment,
                "moment_position_m": moment_x,
                "deflection_mm": max(0.0, self.deflection(deflection_x) * 1000),
                "deflection_position_m": deflection_x,
                "absolute_shear_kn": maximum_shear,
            },
            "equilibrium": {
                "force_residual_kn": self.left_reaction + self.right_reaction - self.q * self.length - self.p,
                "moment_residual_kn_m": self.right_reaction * self.length - self.q * self.length ** 2 / 2 - self.p * self.a,
            },
            "samples": samples,
        }


def calculate(data: Any) -> dict:
    return Beam(BeamInput.from_dict(data)).result()
