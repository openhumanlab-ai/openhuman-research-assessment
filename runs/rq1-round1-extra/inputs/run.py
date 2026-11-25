#!/usr/bin/env python3
"""Small, dependency-free runner for separate persona choice requests."""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_jsonl(path, value):
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")
        handle.flush()


def records(raw, name):
    result = []
    for number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{name}:{number}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{name}:{number}: expected a JSON object")
        result.append(row)
    if not result:
        raise ValueError(f"{name}: no records")
    return result


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def indexed(rows, field):
    result = {}
    for row in rows:
        key = row.get(field)
        if not nonempty(key) or key in result:
            raise ValueError(f"Missing or duplicate {field}")
        result[key] = row
    return result


def load_inputs(args):
    # Read each input once; saved snapshots and requests use those same bytes.
    paths = {"personas.jsonl": args.personas, "scenarios.jsonl": args.scenarios,
             "trials.jsonl": args.trials, "decision.txt": args.prompt}
    raw = {name: path.read_bytes() for name, path in paths.items()}
    personas = indexed(records(raw["personas.jsonl"], "personas"), "persona_id")
    scenarios = indexed(records(raw["scenarios.jsonl"], "scenarios"), "scenario_id")
    trials = records(raw["trials.jsonl"], "trials")
    indexed(trials, "trial_id")
    for persona in personas.values():
        if set(persona) != {"persona_id", "text"} or not nonempty(persona["text"]):
            raise ValueError("Each persona needs exactly persona_id and nonempty text")
    for scenario in scenarios.values():
        if set(scenario) != {"scenario_id", "context", "options"}:
            raise ValueError("Each scenario needs exactly scenario_id, context, options")
        options = scenario["options"]
        if not nonempty(scenario["context"]) or not isinstance(options, list) or len(options) < 2:
            raise ValueError("Each scenario needs context and at least two options")
        if any(not isinstance(option, dict) for option in options):
            raise ValueError("Scenario options must be objects")
        indexed(options, "option_id")
        if any(set(option) != {"option_id", "text"} or not nonempty(option["text"])
               for option in options):
            raise ValueError("Each option needs exactly option_id and nonempty text")
    seen = set()
    for trial in trials:
        if set(trial) != {"trial_id", "persona_id", "scenario_id", "condition", "replicate_id"}:
            raise ValueError("Each trial needs trial_id, persona_id, scenario_id, condition, replicate_id")
        if not all(nonempty(trial[key]) for key in ("scenario_id", "condition", "replicate_id")):
            raise ValueError("Trial scenario_id, condition, and replicate_id must be nonempty strings")
        pid = trial["persona_id"]
        if pid is not None and (not isinstance(pid, str) or pid not in personas):
            raise ValueError(f"Unknown persona_id in trial {trial['trial_id']}")
        if trial["scenario_id"] not in scenarios:
            raise ValueError(f"Unknown scenario_id in trial {trial['trial_id']}")
        key = (pid, trial["scenario_id"], trial["condition"], trial["replicate_id"])
        if key in seen:
            raise ValueError("Duplicate trial combination; use distinct replicate_id values")
        seen.add(key)
    prompt = raw["decision.txt"].decode("utf-8").strip()
    if not prompt:
        raise ValueError("System prompt is empty")
    return raw, personas, scenarios, trials, prompt


def read_config(path):
    # Small literal KEY=VALUE parser. Never executes shell code or prints values.
    values = {}
    if path.exists():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                raise ValueError(f"Environment file line {number} must use KEY=VALUE")
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
                value = value[1:-1]
            values[key] = value
    for key in ("LLM_API_KEY", "LLM_MODEL", "LLM_BASE_URL", "OPENAI_API_KEY", "OPENAI_MODEL"):
        if key in os.environ:
            values[key] = os.environ[key]
    return values


def endpoint(base):
    parsed = urllib.parse.urlsplit(base)
    if (parsed.username or parsed.password or parsed.query or parsed.fragment
            or not parsed.hostname):
        raise ValueError("LLM_BASE_URL must be a base URL without credentials, query, or fragment")
    local = parsed.hostname in ("localhost", "127.0.0.1", "::1")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and local):
        raise ValueError("Use HTTPS for the model endpoint (HTTP is allowed for local tests)")
    return base.rstrip("/") + "/chat/completions"


def make_request(trial, personas, scenarios, prompt, model, args):
    scenario = scenarios[trial["scenario_id"]]
    persona = personas[trial["persona_id"]]["text"] if trial["persona_id"] is not None else None
    # Only persona text, situation, and choices are shown; no condition labels.
    context = {"persona_description": persona, "situation": scenario["context"],
               "options": scenario["options"]}
    body = {"model": model,
            "messages": [{"role": "system", "content": prompt},
                         {"role": "user", "content": json.dumps(context, ensure_ascii=False)}],
            "response_format": {"type": "json_object"},
            "max_completion_tokens": args.max_completion_tokens}
    if args.temperature is not None:
        body["temperature"] = args.temperature
    return {"trial": trial, "body": body}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward authentication to a redirect target.
        return None


class HTTPFailure(RuntimeError):
    def __init__(self, status, retry_after_seconds=None):
        super().__init__(f"HTTP {status}; no automatic retry was made")
        self.status = status
        self.retry_after_seconds = retry_after_seconds


def send(url, key, body, timeout):
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            # A provider should not reflect a key; redact defensively if it does.
            text = text.replace(key, "[REDACTED]")
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                # A malformed successful reply is an observed bad output, not
                # a reason to abandon the remaining trials.
                value = text
            request_id = response.headers.get("x-request-id")
    except urllib.error.HTTPError as exc:
        # Provider error bodies may contain sensitive material. Do not echo them.
        status = exc.code
        retry_after = None
        try:
            seconds = float((exc.headers or {}).get("Retry-After", ""))
            if math.isfinite(seconds) and seconds >= 0:
                retry_after = seconds
        except (TypeError, ValueError):
            pass
        exc.close()
        raise HTTPFailure(status, retry_after) from None
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException):
        raise RuntimeError("Connection failed, was incomplete, or timed out; no automatic retry was made") from None
    return value, request_id


def parse_choice(response, option_ids):
    if not isinstance(response, dict):
        raise ValueError("Provider response is not a JSON object")
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ValueError("Expected one model response choice")
    choice = choices[0]
    if choice.get("finish_reason") != "stop":
        raise ValueError("Model did not finish normally; check output limits or refusal")
    message = choice.get("message")
    if not isinstance(message, dict) or message.get("refusal"):
        raise ValueError("Missing or refused model message")
    content = message.get("content")
    if not nonempty(content):
        raise ValueError("Model returned no text")
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("Model content is not valid JSON") from None
    if not isinstance(result, dict) or set(result) != {"choice_id", "explanation"}:
        raise ValueError("Model content must have exactly choice_id and explanation")
    if not isinstance(result["choice_id"], str) or result["choice_id"] not in option_ids:
        raise ValueError("Model returned an option_id not present in the trial")
    if not nonempty(result["explanation"]):
        raise ValueError("Model explanation is empty")
    return result


def export_remaining(args):
    """Write only unfinished/transport-failed trials; never make model calls."""
    manifest = json.loads((args.from_run / "manifest.json").read_text(encoding="utf-8"))
    request_bytes = (args.from_run / "requests.jsonl").read_bytes()
    if digest(request_bytes) != manifest["requests_sha256"]:
        raise ValueError("Saved request file changed; do not resume from altered evidence")
    requests = records(request_bytes, "saved requests")
    outcomes = {}
    results_path = args.from_run / "results.jsonl"
    if results_path.exists() and results_path.stat().st_size:
        for row in records(results_path.read_bytes(), "saved results"):
            trial_id = row["trial"]["trial_id"]
            if trial_id in outcomes:
                raise ValueError("Multiple results for one trial in the source run")
            outcomes[trial_id] = row["status"]
    finished = {"ok"} if args.include_invalid else {"ok", "invalid_output"}
    pending = [r["trial"] for r in requests
               if outcomes.get(r["trial"]["trial_id"]) not in finished]
    if args.out.exists():
        raise ValueError("Output trials file already exists; choose a new path")
    if not pending:
        print("No remaining trials. Invalid outputs remain recorded observations unless --include-invalid is chosen.")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        for trial in pending:
            handle.write(json.dumps(trial, ensure_ascii=False) + "\n")
    print(f"Wrote {len(pending)} trial(s) to {args.out}; no model calls. Keep the original run and reuse its input snapshots/settings.")
    return 0


def execute(args):
    if args.command == "remaining":
        return export_remaining(args)
    raw, personas, scenarios, trials, prompt = load_inputs(args)
    if args.command == "check":
        print(f"Valid: {len(personas)} descriptions, {len(scenarios)} scenarios, {len(trials)} example trial(s). No model calls.")
        return 0
    if args.max_calls < 1 or len(trials) > args.max_calls:
        raise ValueError("Trial count exceeds --max-calls, or max-calls is below 1")
    if args.max_completion_tokens < 1 or args.timeout <= 0 or not math.isfinite(args.timeout):
        raise ValueError("Token limit and timeout must be positive")
    if args.temperature is not None and (not math.isfinite(args.temperature) or not 0 <= args.temperature <= 2):
        raise ValueError("Temperature must be between 0 and 2")
    config = read_config(args.env_file)
    key = (config.get("LLM_API_KEY") or config.get("OPENAI_API_KEY") or "").strip()
    model = (config.get("LLM_MODEL") or config.get("OPENAI_MODEL") or "").strip()
    live = args.command == "run"
    if live and (not key or not model):
        raise ValueError("Live run needs LLM_API_KEY and LLM_MODEL. See SETUP.md; no call was made.")
    model = model or "NOT_CONFIGURED_PREVIEW_ONLY"
    url = endpoint(config.get("LLM_BASE_URL") or "https://api.openai.com/v1")
    requests = [make_request(t, personas, scenarios, prompt, model, args) for t in trials]
    snapshots = dict(raw)
    snapshots["run.py"] = Path(__file__).read_bytes()
    if args.out.exists():
        raise ValueError("Output directory already exists; choose a new path")
    args.out.mkdir(parents=True)
    (args.out / "inputs").mkdir()
    for name, value in snapshots.items():
        (args.out / "inputs" / name).write_bytes(value)
    for request in requests:
        append_jsonl(args.out / "requests.jsonl", request)
    manifest = {
        "schema_version": 2, "mode": "live" if live else "prepare",
        "status": "running" if live else "prepared", "started_at": stamp(),
        "finished_at": None, "requested_model": model, "endpoint": url,
        "settings": {"max_completion_tokens": args.max_completion_tokens,
                     "temperature": args.temperature, "timeout_seconds": args.timeout,
                     "automatic_retries": 0, "conversation_per_trial": "fresh"},
        "planned_calls": len(trials), "attempted_calls": 0, "successful_calls": 0,
        "invalid_outputs": 0, "transport_errors": 0,
        "input_sha256": {name: digest(value) for name, value in snapshots.items()},
        "requests_sha256": digest((args.out / "requests.jsonl").read_bytes()),
        "note": "A prepared run has no responses. Live outputs are model simulations, not human data.",
    }
    if not live:
        manifest["finished_at"] = stamp()
        write_json(args.out / "manifest.json", manifest)
        print(f"Prepared {len(trials)} request(s) in {args.out}; no model calls or decisions generated.")
        return 0
    write_json(args.out / "manifest.json", manifest)
    print(f"Running {len(trials)} separate request(s); saving to {args.out}.", flush=True)
    failed = False
    try:
        for request in requests:
            trial = request["trial"]
            result = {"trial": trial, "started_at": stamp(), "status": "error"}
            started = time.monotonic()
            manifest["attempted_calls"] += 1
            write_json(args.out / "manifest.json", manifest)
            try:
                response, request_id = send(url, key, request["body"], args.timeout)
                result.update({"raw_response": response, "request_id": request_id})
                if isinstance(response, dict):
                    result.update({"returned_model": response.get("model"), "usage": response.get("usage")})
                option_ids = {o["option_id"] for o in scenarios[trial["scenario_id"]]["options"]}
                try:
                    result["parsed"] = parse_choice(response, option_ids)
                    result["status"] = "ok"
                    manifest["successful_calls"] += 1
                except ValueError as exc:
                    result["status"] = "invalid_output"
                    result["error"] = str(exc)
                    manifest["invalid_outputs"] += 1
            except RuntimeError as exc:
                result["error"] = str(exc)
                manifest["transport_errors"] += 1
                if isinstance(exc, HTTPFailure):
                    result["http_status"] = exc.status
                    result["retry_after_seconds"] = exc.retry_after_seconds
            except KeyboardInterrupt:
                result["status"] = "interrupted"
                result["error"] = "Interrupted during request; provider outcome and usage are unknown."
                raise
            finally:
                result["elapsed_seconds"] = round(time.monotonic() - started, 3)
                result["finished_at"] = stamp()
                append_jsonl(args.out / "results.jsonl", result)
            failed = result["status"] == "error"
            write_json(args.out / "manifest.json", manifest)
            print(f"{trial['trial_id']}: {result['status']}", flush=True)
            if failed:
                print("Stopped on a transport/HTTP error. Inspect the saved result; use 'remaining' to export unfinished trials. No automatic retry was made.", file=sys.stderr)
                break
        manifest["status"] = ("failed" if failed else
                              "completed_with_invalid_outputs" if manifest["invalid_outputs"] else "completed")
    except BaseException:
        manifest["status"] = "interrupted"
        raise
    finally:
        manifest["finished_at"] = stamp()
        manifest["unattempted_calls"] = len(trials) - manifest["attempted_calls"]
        write_json(args.out / "manifest.json", manifest)
    print(f"{manifest['status']}: {manifest['successful_calls']} valid, {manifest['invalid_outputs']} invalid, {manifest['transport_errors']} transport errors, {manifest['unattempted_calls']} unattempted.")
    return 1 if failed else 0


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    remaining = commands.add_parser("remaining", help="Export unfinished trials without making model calls")
    remaining.add_argument("--from-run", type=Path, required=True)
    remaining.add_argument("--out", type=Path, required=True)
    remaining.add_argument("--include-invalid", action="store_true", help="Explicitly include malformed outputs for another attempt; retain their original results")
    for name in ("check", "prepare", "run"):
        command = commands.add_parser(name)
        command.add_argument("--personas", type=Path, default=ROOT / "data/personas.jsonl")
        command.add_argument("--scenarios", type=Path, default=ROOT / "data/scenarios.jsonl")
        command.add_argument("--trials", type=Path, default=ROOT / "examples/smoke_trials.jsonl")
        command.add_argument("--prompt", type=Path, default=ROOT / "prompts/decision.txt")
        if name != "check":
            command.add_argument("--out", type=Path, required=True)
            command.add_argument("--env-file", type=Path, default=ROOT / ".env")
            command.add_argument("--max-calls", type=int, default=200)
            command.add_argument("--max-completion-tokens", type=int, default=2048)
            command.add_argument("--timeout", type=float, default=60)
            command.add_argument("--temperature", type=float)
    return result


def main():
    try:
        return execute(parser().parse_args())
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted; inspect the saved run before retrying.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
