import http.client
import json
import threading
import unittest

from market_observatory.server import create_server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(method, path, body, headers or {})
        response = conn.getresponse()
        data = response.read()
        conn.close()
        return response.status, data, response.headers

    def test_static_and_token(self):
        status, body, headers = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(self.server.token.encode(), body)
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])

    def test_demo_analysis_and_exports(self):
        h = {
            "Content-Type": "application/json",
            "Origin": f"http://127.0.0.1:{self.port}",
            "X-Research-Token": self.server.token,
        }
        status, body, _ = self.request("POST", "/api/analyze", json.dumps({"demo": True}), h)
        self.assertEqual(status, 200)
        r = json.loads(body)
        self.assertEqual(len(r["result"]["assets"]), 4)
        self.assertIn("<!doctype html>", r["exports"]["html"])

    def test_cross_origin_denied(self):
        for headers in [
            {},
            {"Origin": "https://evil.example", "X-Research-Token": self.server.token},
        ]:
            self.assertEqual(self.request("POST", "/api/analyze", "{}", headers)[0], 403)

    def test_host_rebinding_denied(self):
        self.assertEqual(self.request("GET", "/", headers={"Host": "evil.example"})[0], 403)

    def test_no_traversal(self):
        self.assertEqual(self.request("GET", "/../engine.py")[0], 404)

    def test_bad_json(self):
        h = {
            "Origin": f"http://127.0.0.1:{self.port}",
            "X-Research-Token": self.server.token,
            "Content-Type": "application/json",
        }
        for body in [
            "[]",
            '{"demo":true,"settings":[]}',
            '{"demo":true,"settings":{"arbitrary":42}}',
            "{bad",
            '{"demo":true,"settings":{"mode":[]}}',
        ]:
            self.assertEqual(self.request("POST", "/api/analyze", body, h)[0], 400)

    def test_import_payload_and_size_boundary(self):
        from test_engine import CSV, META

        h = {
            "Content-Type": "application/json",
            "Origin": f"http://127.0.0.1:{self.port}",
            "X-Research-Token": self.server.token,
        }
        status, body, _ = self.request(
            "POST",
            "/api/analyze",
            json.dumps({"csv": CSV, "metadata": META, "settings": {"mode": "buy_hold"}}),
            h,
        )
        self.assertEqual(status, 200)
        self.assertAlmostEqual(json.loads(body)["result"]["portfolio"]["total_return"], -0.01)
        self.assertEqual(
            self.request("POST", "/api/analyze", "{}", {**h, "Content-Length": "999999999"})[0],
            413,
        )

    def test_non_ascii_token_is_rejected(self):
        headers = {"Origin": f"http://127.0.0.1:{self.port}", "X-Research-Token": "é"}
        self.assertEqual(self.request("POST", "/api/analyze", "{}", headers)[0], 403)

    def test_browser_decoder_asset_and_exact_import_source_hash(self):
        import hashlib

        from test_engine import CSV, META

        status, decoder, _ = self.request("GET", "/csv-input.js")
        self.assertEqual(status, 200)
        self.assertIn(b"function decodeCsvBytes", decoder)
        raw = ("\ufeff" + CSV.replace("\n", "\r\n")).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Origin": f"http://127.0.0.1:{self.port}",
            "X-Research-Token": self.server.token,
        }
        status, body, _ = self.request(
            "POST",
            "/api/analyze",
            json.dumps({"csv": raw.decode("utf-8"), "metadata": META}),
            headers,
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            json.loads(body)["result"]["provenance"]["source_sha256"],
            hashlib.sha256(raw).hexdigest(),
        )
