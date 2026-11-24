"""Offline checks for the runner's data custody and request behaviour."""
import hashlib
import http.client
import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

import run


def response(choice="cook"):
    return {"model": "test-model", "usage": {"total_tokens": 12},
            "choices": [{"finish_reason": "stop", "message": {
                "content": json.dumps({"choice_id": choice, "explanation": "Synthetic test response."})}}]}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env_patch = patch.dict(os.environ, {}, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.env = self.root / "test.env"
        self.env.write_text("LLM_API_KEY=unit-test-credential\nLLM_MODEL=test-model\n")

    def args(self, command="prepare", trials=None):
        return run.parser().parse_args([
            command, "--out", str(self.root / "output"), "--env-file", str(self.env),
            "--trials", str(trials or run.ROOT / "examples/smoke_trials.jsonl")])

    def repeated_trials(self, count=2):
        row = json.loads((run.ROOT / "examples/smoke_trials.jsonl").read_text())
        rows = [dict(row, trial_id=f"t{i}", replicate_id=f"r{i}") for i in range(count)]
        path = self.root / "trials.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
        return path

    def manifest(self):
        return json.loads((self.root / "output/manifest.json").read_text())

    def test_prepare_is_offline_and_keeps_labels_out_of_messages(self):
        self.env.unlink()
        with patch.object(run, "send", side_effect=AssertionError("unexpected live call")):
            self.assertEqual(run.execute(self.args()), 0)
        out = self.root / "output"
        self.assertFalse((out / "results.jsonl").exists())
        request = json.loads((out / "requests.jsonl").read_text())
        self.assertEqual(request["trial"]["condition"], "connection-check")
        messages = request["body"]["messages"]
        self.assertEqual(len(messages), 2)
        user = json.loads(messages[1]["content"])
        self.assertEqual(set(user), {"persona_description", "situation", "options"})
        self.assertNotIn("connection-check", json.dumps(messages))
        for name, expected in self.manifest()["input_sha256"].items():
            self.assertEqual(hashlib.sha256((out / "inputs" / name).read_bytes()).hexdigest(), expected)

    def test_fresh_conversations_and_saved_results(self):
        calls = []

        def fake(url, key, body, timeout):
            calls.append(body)
            return response(), "test-request-id"

        with patch.object(run, "send", side_effect=fake):
            self.assertEqual(run.execute(self.args("run", self.repeated_trials())), 0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(len(calls[1]["messages"]), 2)
        self.assertEqual(self.manifest()["successful_calls"], 2)
        self.assertEqual(self.manifest()["status"], "completed")
        for path in (self.root / "output").rglob("*"):
            if path.is_file():
                self.assertNotIn("unit-test-credential", path.read_text())

    def test_invalid_output_preserves_response_and_continues(self):
        with patch.object(run, "send", side_effect=[(response("invented-option"), None), (response(), None)]) as send:
            self.assertEqual(run.execute(self.args("run", self.repeated_trials())), 0)
        self.assertEqual(send.call_count, 2)
        saved = [json.loads(line) for line in (self.root / "output/results.jsonl").read_text().splitlines()]
        self.assertEqual([r["status"] for r in saved], ["invalid_output", "ok"])
        self.assertIn("raw_response", saved[0])
        self.assertEqual(self.manifest()["status"], "completed_with_invalid_outputs")
        self.assertEqual(self.manifest()["planned_calls"], 2)
        self.assertEqual(self.manifest()["attempted_calls"], 2)
        self.assertEqual(self.manifest()["invalid_outputs"], 1)
        self.assertEqual(self.manifest()["successful_calls"], 1)

    def test_malformed_and_truncated_replies_do_not_stop_later_trials(self):
        invalid_json = response()
        invalid_json["choices"][0]["message"]["content"] = "not JSON"
        truncated = response()
        truncated["choices"][0]["finish_reason"] = "length"
        for index, bad in enumerate(["not a JSON response", [], invalid_json, truncated]):
            with self.subTest(index=index):
                args = self.args("run", self.repeated_trials())
                args.out = self.root / f"case-{index}"
                with patch.object(run, "send", side_effect=[(bad, None), (response(), None)]) as send:
                    self.assertEqual(run.execute(args), 0)
                self.assertEqual(send.call_count, 2)
                rows = [json.loads(line) for line in (args.out / "results.jsonl").read_text().splitlines()]
                self.assertEqual([r["status"] for r in rows], ["invalid_output", "ok"])
                self.assertEqual(rows[0]["raw_response"], bad)

    def test_http_error_stops_and_remaining_export_skips_recorded_invalids(self):
        calls = [(response(), None), (response("invented-option"), None), run.HTTPFailure(429, 10)]
        with patch.object(run, "send", side_effect=calls) as send:
            self.assertEqual(run.execute(self.args("run", self.repeated_trials(4))), 1)
        self.assertEqual(send.call_count, 3)
        self.assertEqual(self.manifest()["status"], "failed")
        self.assertEqual(self.manifest()["unattempted_calls"], 1)
        saved = [json.loads(line) for line in (self.root / "output/results.jsonl").read_text().splitlines()]
        self.assertEqual(saved[-1]["http_status"], 429)
        self.assertEqual(saved[-1]["retry_after_seconds"], 10)
        for include_invalid in (False, True):
            output = self.root / f"remaining-{include_invalid}.jsonl"
            argv = ["remaining", "--from-run", str(self.root / "output"), "--out", str(output)]
            if include_invalid:
                argv.append("--include-invalid")
            with patch.object(run, "send") as no_calls:
                self.assertEqual(run.execute(run.parser().parse_args(argv)), 0)
            no_calls.assert_not_called()
            ids = [json.loads(line)["trial_id"] for line in output.read_text().splitlines()]
            self.assertEqual(ids, ["t1", "t2", "t3"] if include_invalid else ["t2", "t3"])

    def test_missing_config_makes_no_call_or_output_directory(self):
        self.env.unlink()
        with patch.object(run, "send") as send, self.assertRaisesRegex(ValueError, "needs LLM_API_KEY"):
            run.execute(self.args("run"))
        send.assert_not_called()
        self.assertFalse((self.root / "output").exists())

    def test_duplicate_replicate_rejected_before_spending(self):
        path = self.repeated_trials()
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[1]["replicate_id"] = rows[0]["replicate_id"]
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
        with patch.object(run, "send") as send, self.assertRaisesRegex(ValueError, "Duplicate trial combination"):
            run.execute(self.args("run", path))
        send.assert_not_called()

    def test_output_directory_cannot_be_overwritten(self):
        out = self.root / "output"
        out.mkdir()
        marker = out / "existing.txt"
        marker.write_text("preserve me")
        with self.assertRaisesRegex(ValueError, "already exists"):
            run.execute(self.args())
        self.assertEqual(marker.read_text(), "preserve me")

    def test_http_error_body_not_exposed_and_no_retry(self):
        opener = Mock()
        opener.open.side_effect = urllib.error.HTTPError(
            "https://api.example.test/v1", 401, "error", {}, io.BytesIO(b"unit-test-credential"))
        with patch.object(run.urllib.request, "build_opener", return_value=opener):
            with self.assertRaisesRegex(RuntimeError, "HTTP 401") as error:
                run.send("https://api.example.test/v1", "unit-test-credential", {}, 2)
        self.assertNotIn("unit-test-credential", str(error.exception))
        self.assertEqual(opener.open.call_count, 1)

    def test_http_retry_after_is_retained(self):
        opener = Mock()
        opener.open.side_effect = urllib.error.HTTPError(
            "https://api.example.test/v1", 429, "rate limit", {"Retry-After": "12"}, io.BytesIO(b"private"))
        with patch.object(run.urllib.request, "build_opener", return_value=opener):
            with self.assertRaises(run.HTTPFailure) as error:
                run.send("https://api.example.test/v1", "unit-test-credential", {}, 2)
        self.assertEqual(error.exception.status, 429)
        self.assertEqual(error.exception.retry_after_seconds, 12)

    def test_transport_preserves_non_json_success_reply(self):
        reply = Mock()
        reply.read.return_value = b"invalid provider reply"
        reply.headers = {}
        opened = Mock()
        opened.__enter__ = Mock(return_value=reply)
        opened.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = opened
        with patch.object(run.urllib.request, "build_opener", return_value=opener):
            saved, _ = run.send("https://api.example.test/v1", "unit-test-credential", {}, 2)
        self.assertEqual(saved, "invalid provider reply")

    def test_transport_serializes_json_and_redacts_reflected_key(self):
        payload = response()
        payload["provider_note"] = "unit-test-credential"
        reply = Mock()
        reply.read.return_value = json.dumps(payload).encode("utf-8")
        reply.headers = {"x-request-id": "local-stub-request"}
        opened = Mock()
        opened.__enter__ = Mock(return_value=reply)
        opened.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = opened
        body = {"model": "test-model", "messages": [{"role": "user", "content": "£7"}]}
        with patch.object(run.urllib.request, "build_opener", return_value=opener):
            saved, request_id = run.send("https://api.example.test/v1", "unit-test-credential", body, 2)
        request = opener.open.call_args.args[0]
        self.assertEqual(json.loads(request.data), body)
        self.assertEqual(request.get_header("Authorization"), "Bearer unit-test-credential")
        self.assertEqual(request_id, "local-stub-request")
        self.assertNotIn("unit-test-credential", json.dumps(saved))

    def test_request_cap_is_checked_before_spending(self):
        args = self.args("run", self.repeated_trials())
        args.max_calls = 1
        with patch.object(run, "send") as send, self.assertRaisesRegex(ValueError, "max-calls"):
            run.execute(args)
        send.assert_not_called()
        self.assertFalse((self.root / "output").exists())

    def test_unknown_reference_is_checked_before_spending(self):
        path = self.repeated_trials()
        row = json.loads(path.read_text().splitlines()[0])
        row["scenario_id"] = "missing-scenario"
        path.write_text(json.dumps(row) + "\n")
        with patch.object(run, "send") as send, self.assertRaisesRegex(ValueError, "Unknown scenario_id"):
            run.execute(self.args("run", path))
        send.assert_not_called()

    def test_interrupt_is_recorded_without_fabricating_response(self):
        with patch.object(run, "send", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            run.execute(self.args("run"))
        self.assertEqual(self.manifest()["status"], "interrupted")
        self.assertEqual(self.manifest()["attempted_calls"], 1)
        saved = json.loads((self.root / "output/results.jsonl").read_text())
        self.assertEqual(saved["status"], "interrupted")
        self.assertIn("unknown", saved["error"])
        self.assertNotIn("raw_response", saved)
        self.assertNotIn("parsed", saved)

    def test_incomplete_http_response_is_saved_as_failed_attempt(self):
        reply = Mock()
        reply.read.side_effect = http.client.IncompleteRead(b"partial", 40)
        opened = Mock()
        opened.__enter__ = Mock(return_value=reply)
        opened.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = opened
        with patch.object(run.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(run.execute(self.args("run", self.repeated_trials())), 1)
        self.assertEqual(opener.open.call_count, 1)
        saved = json.loads((self.root / "output/results.jsonl").read_text())
        self.assertEqual(saved["status"], "error")
        self.assertIn("incomplete", saved["error"])
        self.assertNotIn("parsed", saved)
        self.assertEqual(self.manifest()["status"], "failed")
        self.assertEqual(self.manifest()["attempted_calls"], 1)
        self.assertEqual(self.manifest()["successful_calls"], 0)

    def test_custom_inputs_are_used_and_snapshotted(self):
        personas = [json.loads(line) for line in (run.ROOT / "data/personas.jsonl").read_text().splitlines()]
        personas[0]["text"] = "Custom persona for this test."
        scenarios = [json.loads(line) for line in (run.ROOT / "data/scenarios.jsonl").read_text().splitlines()]
        scenarios[0]["context"] = "Custom scenario for this test."
        for name, rows in [("personas.jsonl", personas), ("scenarios.jsonl", scenarios)]:
            (self.root / name).write_text("".join(json.dumps(row) + "\n" for row in rows))
        (self.root / "decision.txt").write_text("Custom test prompt requesting JSON.")
        args = run.parser().parse_args([
            "prepare", "--out", str(self.root / "output"), "--env-file", str(self.env),
            "--personas", str(self.root / "personas.jsonl"),
            "--scenarios", str(self.root / "scenarios.jsonl"),
            "--prompt", str(self.root / "decision.txt")])
        with patch.object(run, "send", side_effect=AssertionError("unexpected live call")):
            run.execute(args)
        saved = json.loads((self.root / "output/requests.jsonl").read_text())
        messages = saved["body"]["messages"]
        self.assertEqual(messages[0]["content"], "Custom test prompt requesting JSON.")
        user = json.loads(messages[1]["content"])
        self.assertEqual(user["persona_description"], personas[0]["text"])
        self.assertEqual(user["situation"], scenarios[0]["context"])
        for name in ("personas.jsonl", "scenarios.jsonl", "decision.txt"):
            self.assertEqual((self.root / "output/inputs" / name).read_bytes(), (self.root / name).read_bytes())

    def test_endpoint_rejects_embedded_credentials_and_remote_http(self):
        for value in ("https://name:password@example.test/v1", "http://example.test/v1",
                      "https://example.test/v1?key=value"):
            with self.assertRaises(ValueError):
                run.endpoint(value)

    def test_no_persona_request_is_supported(self):
        path = self.repeated_trials()
        row = json.loads(path.read_text().splitlines()[0])
        row["persona_id"] = None
        path.write_text(json.dumps(row) + "\n")
        run.execute(self.args(trials=path))
        request = json.loads((self.root / "output/requests.jsonl").read_text())
        self.assertIsNone(json.loads(request["body"]["messages"][1]["content"])["persona_description"])


if __name__ == "__main__":
    unittest.main()
