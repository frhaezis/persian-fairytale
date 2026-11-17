"""Protocol tests: a loopback fixture is NOT evidence of LLM inference."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model_adapter import run_local_agent


class LocalAgentTests(unittest.TestCase):
    def run_fixture(self, responses, goal="Прочитай запись ledger и объясни её", budget=3):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                received.append({"path": self.path, **payload})
                index = min(len(received)-1, len(responses)-1)
                content = responses[index]
                if not isinstance(content, str):
                    content = json.dumps(content)
                body = json.dumps({"choices":[{"message":{"role":"assistant","content":content}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = run_local_agent(f"http://127.0.0.1:{server.server_port}/v1", "fixture-not-LLM", goal, budget)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        return result, received

    def test_actual_http_tool_observation_and_followup(self):
        result, requests = self.run_fixture([
            {"tool":"lookup_record","arguments":{"id":"ledger"}},
            {"answer":"Порог выбирают на validation, test оценивают один раз."}])
        self.assertTrue(result["success"])
        self.assertEqual(result["mode"], "real-local-agent")
        self.assertEqual(result["stoppedReason"], "final_answer")
        self.assertEqual((result["modelCalls"], result["toolCalls"]), (2,1))
        self.assertEqual(requests[0]["path"], "/v1/chat/completions")
        self.assertEqual(requests[1]["messages"][-1]["role"], "user")
        self.assertIn("Test-набор", requests[1]["messages"][-1]["content"])
        self.assertEqual(result["trace"][0]["observation"]["mode"], "deterministic-game-tool")

    def test_budget_counts_model_responses_and_does_not_fake_success(self):
        result, requests = self.run_fixture([{"tool":"lookup_record","arguments":{"id":"canal"}}], budget=2)
        self.assertFalse(result["success"])
        self.assertEqual(result["stoppedReason"], "budget")
        self.assertEqual(len(requests), 2)
        self.assertEqual(result["toolCalls"], 2)

    def test_invalid_actions_never_reach_tools(self):
        for response in ["not JSON", {"tool":"read_private_file","arguments":{}},
                         {"tool":"read_gate","arguments":{"gate":"east","extra":"x"}},
                         {"tool":"set_gate","arguments":{"threshold":True}},
                         {"answer":"","unexpected":True}]:
            with self.subTest(response=response):
                result, requests = self.run_fixture([response])
                self.assertFalse(result["success"])
                self.assertEqual(result["stoppedReason"], "invalid_action")
                self.assertEqual(result["toolCalls"], 0)
                self.assertEqual(len(requests), 1)

    def test_gate_requires_actual_sensor_and_tool_stop(self):
        open_action = {"tool":"open_gate","arguments":{"gate":"east","signal":"turquoise"}}
        result, _ = self.run_fixture([open_action])
        self.assertFalse(result["success"])
        self.assertEqual(result["toolCalls"], 0)
        result, requests = self.run_fixture([
            {"tool":"read_gate","arguments":{"gate":"east"}}, open_action])
        self.assertTrue(result["success"])
        self.assertEqual(result["stoppedReason"], "tool_stop")
        self.assertEqual(result["toolCalls"], 2)
        self.assertTrue(result["trace"][-1]["observation"]["opened"])
        self.assertEqual(len(requests), 2)

    def test_connection_failure_is_distinct_from_offline_fallback(self):
        result = run_local_agent("http://example.com/v1", "untrusted", "Read a record", 1)
        self.assertFalse(result["success"])
        self.assertEqual(result["stoppedReason"], "api_error")
        self.assertEqual(result["modelCalls"], 0)
        self.assertEqual(result["trace"], [])
        self.assertNotIn("fallback", result)

    def test_invalid_budget_and_goal(self):
        for budget in [0,5,True,1.2]:
            with self.assertRaises(ValueError):
                run_local_agent("http://localhost/v1", "x", "goal", budget)
        with self.assertRaises(ValueError):
            run_local_agent("http://localhost/v1", "x", "", 1)


if __name__ == "__main__":
    unittest.main()
