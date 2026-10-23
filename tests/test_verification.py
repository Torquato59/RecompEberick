import random
import unittest

from backend.beam import Beam, BeamInput, calculate
from verification.cases import BASE
from verification.fem import solve
from verification.report import run_validation


class IndependentVerification(unittest.TestCase):
    def test_ten_benchmarks_and_ninety_comparisons(self):
        report = run_validation()
        self.assertEqual(report["total_cases"], 10)
        self.assertEqual(report["total_checks"], 90)
        for case in report["cases"]:
            for check in case["checks"]:
                with self.subTest(case=case["id"], quantity=check["quantity"]):
                    self.assertTrue(check["passed"], check)

    def test_reference_solver_uniform_load_closed_form(self):
        result = solve(BASE)
        self.assertAlmostEqual(result["left_kn"], 36, places=7)
        self.assertAlmostEqual(result["right_kn"], 36, places=7)
        self.assertAlmostEqual(result["moment_kn_m"], 54, places=7)
        self.assertAlmostEqual(result["deflection_mm"], 3.24, places=7)
        self.assertAlmostEqual(result["left_rotation_mrad"], 1.728, places=7)
        self.assertAlmostEqual(result["right_rotation_mrad"], -1.728, places=7)

    def test_reference_solver_center_point_closed_form(self):
        result = solve(BASE | {"uniform_load_kn_m": 0, "point_load_kn": 20})
        self.assertAlmostEqual(result["moment_kn_m"], 30, places=7)
        self.assertAlmostEqual(result["deflection_mm"], 1.44, places=7)
        self.assertAlmostEqual(result["left_rotation_mrad"], 0.72, places=7)

    def test_reference_displacement_refines_between_nodes(self):
        # Fórmula fechada distinta da interpolação de Hermite da referência.
        x, length, q = 1.234, 6, 12
        ei = 30e6 * 0.2 * 0.5 ** 3 / 12
        exact_mm = q * x * (length ** 3 - 2 * length * x ** 2 + x ** 3) / (24 * ei) * 1000
        coarse = solve(BASE, subdivisions=4)["deflection_at"](x)
        fine = solve(BASE, subdivisions=32)["deflection_at"](x)
        self.assertLess(abs(fine - exact_mm), abs(coarse - exact_mm) / 100)

    def test_seeded_cases_compare_fields_along_span(self):
        randomizer = random.Random(20261023)
        for index in range(24):
            length = randomizer.uniform(2, 12)
            model = BASE | {
                "span_m": length, "point_position_m": length * randomizer.uniform(0.15, 0.85),
                "uniform_load_kn_m": randomizer.uniform(0, 40), "point_load_kn": randomizer.uniform(0, 100),
                "width_m": randomizer.uniform(0.15, 0.4), "height_m": randomizer.uniform(0.3, 0.9),
                "elastic_modulus_gpa": randomizer.uniform(20, 70),
            }
            analytical = Beam(BeamInput.from_dict(model))
            reference = solve(model)
            with self.subTest(case=index):
                self.assertAlmostEqual(reference["left_kn"], analytical.left_reaction, delta=1e-5)
                self.assertAlmostEqual(reference["right_kn"], analytical.right_reaction, delta=1e-5)
                self.assertAlmostEqual(reference["moment_kn_m"], analytical.result()["extrema"]["moment_kn_m"], delta=1e-5)
                for position in [0, 0.23, 0.51, 0.79, 1]:
                    expected = analytical.deflection(position * length) * 1000
                    self.assertAlmostEqual(reference["deflection_at"](position * length), expected, delta=max(1, abs(expected)) * 3e-6)


class AdditionalElasticResults(unittest.TestCase):
    def test_section_stress_rotation_and_units(self):
        result = calculate(BASE)
        self.assertAlmostEqual(result["section"]["area_m2"], 0.1)
        self.assertAlmostEqual(result["section"]["section_modulus_m3"], 1 / 120)
        self.assertAlmostEqual(result["flexural_rigidity_kn_m2"], 62500)
        elastic = result["elastic_results"]
        self.assertAlmostEqual(elastic["max_bending_stress_mpa"], 6.48)
        self.assertAlmostEqual(elastic["max_shear_stress_mpa"], 0.54)
        self.assertAlmostEqual(elastic["left_rotation_mrad"], 1.728)
        self.assertAlmostEqual(elastic["right_rotation_mrad"], -1.728)
        self.assertAlmostEqual(elastic["total_load_kn"], 72)

    def test_rotations_at_every_sample_and_mirrored_loads(self):
        left = calculate(BASE | {"point_load_kn": 23, "point_position_m": 1.7})
        right = calculate(BASE | {"point_load_kn": 23, "point_position_m": 4.3})
        self.assertAlmostEqual(left["elastic_results"]["left_rotation_mrad"], -right["elastic_results"]["right_rotation_mrad"])
        self.assertAlmostEqual(left["extrema"]["deflection_position_m"], 6 - right["extrema"]["deflection_position_m"])
        self.assertAlmostEqual(left["samples"][0]["rotation_mrad"], left["elastic_results"]["left_rotation_mrad"])
        self.assertAlmostEqual(left["samples"][-1]["rotation_mrad"], left["elastic_results"]["right_rotation_mrad"])

    def test_stresses_are_independent_of_modulus_and_scale_with_load(self):
        baseline = calculate(BASE)["elastic_results"]
        stiff = calculate(BASE | {"elastic_modulus_gpa": 60})["elastic_results"]
        loaded = calculate(BASE | {"uniform_load_kn_m": 24})["elastic_results"]
        for key in ["max_bending_stress_mpa", "max_shear_stress_mpa"]:
            self.assertAlmostEqual(baseline[key], stiff[key])
            self.assertAlmostEqual(loaded[key], baseline[key] * 2)
        self.assertAlmostEqual(stiff["left_rotation_mrad"], baseline["left_rotation_mrad"] / 2)


if __name__ == "__main__":
    unittest.main()
