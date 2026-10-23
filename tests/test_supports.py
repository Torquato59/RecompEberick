import itertools
import math
import random
import unittest

from backend.beam import Beam, BeamInput, ValidationError, calculate, polynomial_roots
from verification.cases import BASE
from verification.fem import solve


class SupportCases(unittest.TestCase):
    def model(self, left, right, **changes):
        return Beam(BeamInput.from_dict(BASE | {"support_left": left, "support_right": right} | changes))

    def test_left_cantilever_point_at_free_end(self):
        beam = self.model("fixed", "free", uniform_load_kn_m=0, point_load_kn=20, point_position_m=6)
        result = beam.result()
        self.assertAlmostEqual(result["reactions"]["left_kn"], 20)
        self.assertAlmostEqual(result["reactions"]["right_kn"], 0)
        self.assertAlmostEqual(result["reactions"]["left_moment_kn_m"], 120)
        self.assertAlmostEqual(result["extrema"]["signed_moment_kn_m"], -120)
        self.assertAlmostEqual(result["extrema"]["deflection_mm"], 23.04)
        self.assertAlmostEqual(result["extrema"]["deflection_position_m"], 6)
        self.assertAlmostEqual(result["elastic_results"]["right_rotation_mrad"], 5.76)
        self.assertAlmostEqual(result["elastic_results"]["max_bending_stress_mpa"], 14.4)
        self.assertAlmostEqual(beam.deflection(0), 0)
        self.assertAlmostEqual(beam.slope(0), 0)
        self.assertAlmostEqual(beam.moment(6), 0)
        self.assertAlmostEqual(beam.shear(6, "left"), 20)

    def test_left_cantilever_uniform_closed_form(self):
        beam = self.model("fixed", "free")
        result = beam.result()
        q, length, ei = beam.q, beam.length, beam.ei
        self.assertAlmostEqual(result["reactions"]["left_kn"], q * length)
        self.assertAlmostEqual(result["reactions"]["left_moment_kn_m"], q * length ** 2 / 2)
        self.assertAlmostEqual(result["extrema"]["deflection_mm"], q * length ** 4 / (8 * ei) * 1000)
        for x in [0, 0.8, 2.3, 5.9, 6]:
            expected = q * x ** 2 * (6 * length ** 2 - 4 * length * x + x ** 2) / (24 * ei)
            self.assertAlmostEqual(beam.deflection(x), expected)

    def test_mirrored_cantilever_free_end_load(self):
        left = self.model("fixed", "free", uniform_load_kn_m=0, point_load_kn=20, point_position_m=6)
        right = self.model("free", "fixed", uniform_load_kn_m=0, point_load_kn=20, point_position_m=0)
        result = right.result()
        self.assertAlmostEqual(result["reactions"]["left_kn"], 0)
        self.assertAlmostEqual(result["reactions"]["right_kn"], 20)
        self.assertAlmostEqual(result["reactions"]["right_moment_kn_m"], -120)
        self.assertAlmostEqual(result["extrema"]["deflection_position_m"], 0)
        self.assertAlmostEqual(result["elastic_results"]["left_rotation_mrad"], -5.76)
        for x in [0, 0.3, 2, 4.8, 6]:
            self.assertAlmostEqual(right.deflection(x), left.deflection(6 - x))
            self.assertAlmostEqual(right.moment(x), left.moment(6 - x))

    def test_fixed_fixed_uniform_negative_and_positive_moments(self):
        beam = self.model("fixed", "fixed")
        result = beam.result()
        self.assertAlmostEqual(beam.left_reaction, 36)
        self.assertAlmostEqual(beam.right_reaction, 36)
        self.assertAlmostEqual(beam.left_moment, 36)
        self.assertAlmostEqual(beam.right_moment, -36)
        self.assertAlmostEqual(result["extrema"]["moment_kn_m"], 36)
        self.assertAlmostEqual(result["extrema"]["negative_moment_kn_m"], -36)
        self.assertAlmostEqual(result["extrema"]["positive_moment_kn_m"], 18)
        self.assertAlmostEqual(result["extrema"]["deflection_mm"], 0.648)
        self.assertAlmostEqual(result["extrema"]["deflection_position_m"], 3)
        for x in [0.2, 1.1, 3, 5.8]:
            self.assertAlmostEqual(beam.deflection(x), beam.q * x ** 2 * (6 - x) ** 2 / (24 * beam.ei))

    def test_fixed_fixed_center_point_closed_form(self):
        beam = self.model("fixed", "fixed", uniform_load_kn_m=0, point_load_kn=20)
        result = beam.result()
        self.assertAlmostEqual(result["extrema"]["moment_kn_m"], 20 * 6 / 8)
        self.assertAlmostEqual(result["extrema"]["positive_moment_kn_m"], 20 * 6 / 8)
        self.assertAlmostEqual(result["extrema"]["deflection_mm"], 20 * 6 ** 3 / (192 * beam.ei) * 1000)

    def test_propped_cantilever_uniform_closed_form(self):
        beam = self.model("fixed", "roller")
        result = beam.result()
        self.assertAlmostEqual(beam.left_reaction, 45)
        self.assertAlmostEqual(beam.right_reaction, 27)
        self.assertAlmostEqual(beam.left_moment, 54)
        self.assertAlmostEqual(beam.right_moment, 0)
        self.assertAlmostEqual(result["extrema"]["positive_moment_kn_m"], 30.375)
        self.assertAlmostEqual(result["extrema"]["deflection_position_m"], (15 - math.sqrt(33)) * 6 / 16)
        self.assertAlmostEqual(beam.deflection(3) * 1000, 1.296)
        self.assertAlmostEqual(beam.slope(6) * 1000, -0.864)

    def test_all_stable_combinations_boundaries_and_equilibrium(self):
        valid = 0
        for left, right in itertools.product(["pinned", "roller", "fixed", "free"], repeat=2):
            stable = "fixed" in (left, right) or ("free" not in (left, right) and "pinned" in (left, right))
            with self.subTest(left=left, right=right):
                if not stable:
                    with self.assertRaises(ValidationError):
                        self.model(left, right)
                    continue
                valid += 1
                beam = self.model(left, right, point_load_kn=19, point_position_m=1.7)
                result = beam.result()
                for key in ["force_residual_kn", "moment_residual_kn_m"]:
                    self.assertAlmostEqual(result["equilibrium"][key], 0, places=9)
                for x, support in [(0, left), (6, right)]:
                    if support != "free": self.assertAlmostEqual(beam.deflection(x), 0)
                    if support == "fixed": self.assertAlmostEqual(beam.slope(x), 0)
                    else: self.assertAlmostEqual(beam.moment(x), 0)
                if left == "free": self.assertAlmostEqual(beam.left_reaction, 0)
                if right == "free": self.assertAlmostEqual(beam.right_reaction, 0)
        self.assertEqual(valid, 10)

    def test_seeded_mixed_supports_against_independent_fields(self):
        randomizer = random.Random(20261024)
        combinations = [(a, b) for a, b in itertools.product(["pinned", "roller", "fixed", "free"], repeat=2) if "fixed" in (a, b) or ("free" not in (a, b) and "pinned" in (a, b))]
        for index in range(30):
            left, right = combinations[index % len(combinations)]
            length = randomizer.uniform(2, 12)
            data = BASE | {"support_left": left, "support_right": right, "span_m": length, "point_position_m": length * randomizer.uniform(0.1, 0.9), "uniform_load_kn_m": randomizer.uniform(0, 30), "point_load_kn": randomizer.uniform(0, 100)}
            beam = Beam(BeamInput.from_dict(data))
            result = beam.result()
            reference = solve(data)
            with self.subTest(index=index, left=left, right=right):
                for field in ["left_kn", "right_kn", "left_moment_kn_m", "right_moment_kn_m"]:
                    self.assertAlmostEqual(result["reactions"][field], reference[field], delta=1e-8 + abs(reference[field]) * 3e-6)
                for field in ["moment_kn_m", "deflection_mm"]:
                    self.assertAlmostEqual(result["extrema"][field], reference[field], delta=1e-8 + abs(reference[field]) * 3e-6)
                for fraction in [0, 0.21, 0.55, 0.83, 1]:
                    expected = reference["deflection_at"](fraction * length)
                    self.assertAlmostEqual(beam.deflection(fraction * length) * 1000, expected, delta=1e-7 + abs(expected) * 5e-6)

    def test_legacy_defaults_and_invalid_support_values(self):
        self.assertEqual(calculate(BASE)["supports"], {"left": "pinned", "right": "roller"})
        for value in [None, 1, True, [], "spring", "Fixed"]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                calculate(BASE | {"support_left": value})

    def test_point_load_at_fixed_support_has_no_bending(self):
        for left, right, position in [("fixed", "free", 0), ("free", "fixed", 6)]:
            result = self.model(left, right, uniform_load_kn_m=0, point_load_kn=15, point_position_m=position).result()
            self.assertAlmostEqual(result["extrema"]["moment_kn_m"], 0)
            self.assertAlmostEqual(result["extrema"]["deflection_mm"], 0)

    def test_tangent_and_cubic_stationary_roots(self):
        self.assertTrue(any(abs(x - 0.3) < 1e-9 for x in polynomial_roots([0.09, -0.6, 1], 0, 1)))
        roots = polynomial_roots([-0.08, 0.66, -1.5, 1], 0, 1)
        for expected in [0.2, 0.5, 0.8]:
            self.assertTrue(any(abs(x - expected) < 1e-9 for x in roots))
