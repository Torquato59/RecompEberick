import math
import unittest

from backend.beam import Beam, BeamInput, ValidationError, calculate


BASE = {
    "span_m": 6.0,
    "elastic_modulus_gpa": 30.0,
    "width_m": 0.2,
    "height_m": 0.5,
    "uniform_load_kn_m": 12.0,
    "point_load_kn": 0.0,
    "point_position_m": 3.0,
}


def beam(**changes):
    return Beam(BeamInput.from_dict(BASE | changes))


class AnalyticalCases(unittest.TestCase):
    def assertRelative(self, actual, expected, tolerance=1e-9):
        self.assertAlmostEqual(actual, expected, delta=max(abs(expected), 1e-8) * tolerance)

    def test_uniform_load_closed_form(self):
        model = beam()
        result = model.result()
        q, length, ei = model.q, model.length, model.ei
        self.assertRelative(result["reactions"]["left_kn"], q * length / 2)
        self.assertRelative(result["reactions"]["right_kn"], q * length / 2)
        self.assertRelative(result["extrema"]["moment_kn_m"], q * length ** 2 / 8)
        self.assertRelative(result["extrema"]["deflection_mm"], 5 * q * length ** 4 / (384 * ei) * 1000)
        self.assertRelative(result["extrema"]["deflection_position_m"], length / 2)
        # Valor de referência independente para o exemplo entregue.
        self.assertRelative(result["extrema"]["moment_kn_m"], 54.0)
        self.assertRelative(result["extrema"]["deflection_mm"], 3.24)

    def test_center_point_load_closed_form(self):
        model = beam(uniform_load_kn_m=0, point_load_kn=20)
        result = model.result()
        self.assertRelative(result["reactions"]["left_kn"], 10)
        self.assertRelative(result["reactions"]["right_kn"], 10)
        self.assertRelative(result["extrema"]["moment_kn_m"], model.p * model.length / 4)
        self.assertRelative(result["extrema"]["deflection_mm"], model.p * model.length ** 3 / (48 * model.ei) * 1000)

    def test_eccentric_point_load_closed_form_throughout_span(self):
        model = beam(uniform_load_kn_m=0, point_load_kn=23, point_position_m=1.7)
        length, a = model.length, model.a
        b = length - a
        self.assertRelative(model.left_reaction, model.p * b / length)
        self.assertRelative(model.right_reaction, model.p * a / length)
        for x in [0, 0.4, a, 3.8, 5.3, length]:
            with self.subTest(x=x):
                if x <= a:
                    expected = model.p * b * x / (6 * length * model.ei) * (length ** 2 - b ** 2 - x ** 2)
                else:
                    expected = model.p * a * (length - x) / (6 * length * model.ei) * (length ** 2 - a ** 2 - (length - x) ** 2)
                self.assertRelative(model.deflection(x), expected)
        result = model.result()
        self.assertRelative(result["extrema"]["moment_kn_m"], model.p * a * b / length)
        self.assertRelative(result["extrema"]["deflection_position_m"], length - math.sqrt((length ** 2 - a ** 2) / 3))

    def test_superposition_and_support_conditions(self):
        uniform = beam(point_position_m=2)
        point = beam(uniform_load_kn_m=0, point_load_kn=19, point_position_m=2)
        combined = beam(point_load_kn=19, point_position_m=2)
        for x in [0, 0.8, 2, 2.5, 4.9, 6]:
            with self.subTest(x=x):
                self.assertAlmostEqual(combined.deflection(x), uniform.deflection(x) + point.deflection(x), places=12)
                self.assertAlmostEqual(combined.moment(x), uniform.moment(x) + point.moment(x), places=10)
                self.assertAlmostEqual(combined.shear(x), uniform.shear(x) + point.shear(x), places=10)
        for x in [0, combined.length]:
            self.assertAlmostEqual(combined.moment(x), 0, places=10)
            self.assertAlmostEqual(combined.deflection(x), 0, places=10)

    def test_combined_load_interior_moment_extremum(self):
        # Ra=46 kN; após a=1, V=46−12x−12 e V=0 em x=17/6.
        result = beam(point_load_kn=12, point_position_m=1).result()
        reaction = 36 + 12 * 5 / 6
        expected_x = (reaction - 12) / 12
        self.assertRelative(result["extrema"]["moment_position_m"], expected_x)
        self.assertRelative(result["extrema"]["moment_kn_m"], reaction * expected_x - 6 * expected_x ** 2 - 12 * (expected_x - 1))

    def test_equilibrium_and_shear_jump(self):
        model = beam(point_load_kn=37, point_position_m=2.7)
        result = model.result()
        self.assertAlmostEqual(result["equilibrium"]["force_residual_kn"], 0, places=10)
        self.assertAlmostEqual(result["equilibrium"]["moment_residual_kn_m"], 0, places=10)
        at_point = [s for s in result["samples"] if s["x_m"] == model.a]
        self.assertEqual(len(at_point), 2)
        self.assertRelative(at_point[0]["shear_kn"] - at_point[1]["shear_kn"], model.p)
        self.assertRelative(model.shear(0), model.left_reaction)
        self.assertRelative(model.shear(model.length), -model.right_reaction)

    def test_stiffness_scaling_preserves_forces(self):
        regular = beam().result()
        stiff = beam(elastic_modulus_gpa=60).result()
        self.assertEqual(regular["reactions"], stiff["reactions"])
        self.assertRelative(stiff["extrema"]["deflection_mm"], regular["extrema"]["deflection_mm"] / 2)
        taller = beam(height_m=1).result()
        self.assertRelative(taller["extrema"]["deflection_mm"], regular["extrema"]["deflection_mm"] / 8)

    def test_zero_load_has_no_response(self):
        result = beam(uniform_load_kn_m=0).result()
        self.assertEqual(result["reactions"], {"left_kn": 0, "right_kn": 0})
        for sample in result["samples"]:
            self.assertEqual(sample["shear_kn"], 0)
            self.assertEqual(sample["moment_kn_m"], 0)
            self.assertEqual(sample["deflection_mm"], 0)

    def test_load_at_support_goes_to_that_support(self):
        for position in [0, 6]:
            with self.subTest(position=position):
                result = beam(uniform_load_kn_m=0, point_load_kn=15, point_position_m=position).result()
                self.assertEqual(result["reactions"]["left_kn"], 15 if position == 0 else 0)
                self.assertEqual(result["reactions"]["right_kn"], 15 if position == 6 else 0)
                self.assertAlmostEqual(result["extrema"]["moment_kn_m"], 0)
                self.assertAlmostEqual(result["extrema"]["deflection_mm"], 0)
                self.assertTrue(all(abs(s["shear_kn"]) < 1e-10 for s in result["samples"]))

    def test_maximum_deflection_is_not_bound_to_sample_grid(self):
        model = beam(point_load_kn=120, point_position_m=1.234)
        result = model.result()
        x = result["extrema"]["deflection_position_m"]
        self.assertAlmostEqual(model.slope(x), 0, places=10)
        self.assertGreater(model.deflection(x), model.deflection(x - 0.001))
        self.assertGreater(model.deflection(x), model.deflection(x + 0.001))


class InputValidation(unittest.TestCase):
    def test_invalid_numbers_and_ranges(self):
        for value in [None, "6", True, float("nan"), float("inf"), -1, 0, 101, 10 ** 400]:
            with self.subTest(value=str(value)[:30]), self.assertRaises(ValidationError):
                calculate(BASE | {"span_m": value})
        for name in ["width_m", "height_m", "elastic_modulus_gpa"]:
            with self.subTest(name=name), self.assertRaises(ValidationError):
                calculate(BASE | {name: 0})

    def test_negative_load_and_position_outside_beam(self):
        for changes in [{"uniform_load_kn_m": -1}, {"point_load_kn": -1}, {"point_position_m": 6.01}, {"point_position_m": -0.1}]:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                calculate(BASE | changes)

    def test_missing_unknown_fields_and_non_object(self):
        for data in [[], None, 1, {}, BASE | {"unknown": 1}, {k: v for k, v in BASE.items() if k != "height_m"}]:
            with self.subTest(data=data), self.assertRaises(ValidationError):
                calculate(data)

    def test_range_extremes_remain_finite(self):
        result = calculate(BASE | {"span_m": 100, "height_m": 0.01, "width_m": 0.01, "elastic_modulus_gpa": 0.1, "point_load_kn": 1e6, "uniform_load_kn_m": 1e6})
        for sample in result["samples"]:
            self.assertTrue(all(math.isfinite(sample[key]) for key in ["shear_kn", "moment_kn_m", "deflection_mm"]))


if __name__ == "__main__":
    unittest.main()
