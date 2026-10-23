from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import threading
import unittest

from backend.server import DIST, Handler
from test_beam import BASE


class QuietHandler(Handler):
    def log_message(self, *_args):
        pass


class HTTPIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (DIST / "index.html").is_file():
            raise RuntimeError("Compile a interface com npm run build antes dos testes HTTP.")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, method, path, body=None, headers=None):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        status, result_headers, data = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return status, result_headers, data

    def test_health_and_compiled_assets(self):
        status, headers, body = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        for path, expected in [("/", b"Viga biapoiada"), ("/app.js", b"/api/calculate"), ("/styles.css", b"@media print")]:
            with self.subTest(path=path):
                status, _headers, body = self.request("GET", path)
                self.assertEqual(status, 200)
                self.assertIn(expected, body)

    def test_real_calculation_through_api(self):
        status, _headers, body = self.request("POST", "/api/calculate", json.dumps(BASE), {"Content-Type": "application/json"})
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertAlmostEqual(result["extrema"]["moment_kn_m"], 54)
        self.assertAlmostEqual(result["extrema"]["deflection_mm"], 3.24)
        self.assertGreaterEqual(len(result["samples"]), 201)
        self.assertAlmostEqual(result["elastic_results"]["max_bending_stress_mpa"], 6.48)

    def test_validation_endpoint_returns_independent_comparisons(self):
        status, _headers, body = self.request("GET", "/api/validation")
        self.assertEqual(status, 200)
        report = json.loads(body)
        self.assertTrue(report["passed"])
        self.assertEqual(report["passed_checks"], 231)
        self.assertEqual(report["total_cases"], 21)

    def test_support_reactions_through_api(self):
        for supports, expected_moment, expected_deflection in [
            ({"support_left": "fixed", "support_right": "fixed"}, 36, 0.648),
            ({"support_left": "fixed", "support_right": "free"}, 216, 31.104),
        ]:
            with self.subTest(supports=supports):
                status, _headers, body = self.request("POST", "/api/calculate", json.dumps(BASE | supports), {"Content-Type": "application/json"})
                self.assertEqual(status, 200)
                result = json.loads(body)
                self.assertAlmostEqual(result["reactions"]["left_moment_kn_m"], expected_moment)
                self.assertAlmostEqual(result["extrema"]["deflection_mm"], expected_deflection)

    def test_unstable_supports_rejected_through_api(self):
        for left, right in [("roller", "roller"), ("pinned", "free"), ("free", "free")]:
            status, _headers, body = self.request("POST", "/api/calculate", json.dumps(BASE | {"support_left": left, "support_right": right}), {"Content-Type": "application/json"})
            self.assertEqual(status, 422)
            self.assertIn("instável", json.loads(body)["error"])

    def test_invalid_requests_return_useful_errors(self):
        cases = [
            ("POST", "/api/calculate", "{}", {"Content-Type": "application/json"}, 422),
            ("POST", "/api/calculate", "broken", {"Content-Type": "application/json"}, 400),
            ("POST", "/api/calculate", "{}", {"Content-Type": "text/plain"}, 415),
            ("POST", "/api/calculate", "x" * 17_000, {"Content-Type": "application/json"}, 413),
            ("POST", "/api/unknown", "{}", {"Content-Type": "application/json"}, 404),
            ("GET", "/backend/beam.py", None, {}, 404),
            ("GET", "/../package.json", None, {}, 404),
        ]
        for method, path, body, headers, expected in cases:
            with self.subTest(path=path, expected=expected):
                status, _headers, response = self.request(method, path, body, headers)
                self.assertEqual(status, expected)
                self.assertTrue(json.loads(response)["error"])


if __name__ == "__main__":
    unittest.main()
