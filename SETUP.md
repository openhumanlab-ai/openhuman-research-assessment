# Setup — outside the assessment timer

Use Python **3.10+**. The runner needs no third-party dependencies. Run commands from the repository root.

## Check files and access

```sh
python3 run.py check
python3 run.py prepare --out runs/preview
cp .env.example .env
```

`prepare` makes no API calls and creates no decisions. Inspect `runs/preview/requests.jsonl`. The default trial is a one-call setup example, not a study design.

Ram or Alessandro supplies a company-funded credential, permitted model, and total spend allowance before the timer. Edit `.env` locally. It is ignored by Git. The runner reads `LLM_API_KEY`, `LLM_MODEL`, and `LLM_BASE_URL`; process values override file values for the same variable. `OPENAI_API_KEY` and `OPENAI_MODEL` are fallbacks. Never submit credentials.

The default model is the snapshot used for our materials rehearsal. Confirm it is permitted for your session. The transport uses OpenAI-compatible Chat Completions with JSON-object output and `max_completion_tokens` ([API reference](https://developers.openai.com/api/reference/resources/chat)).

```sh
python3 run.py run --out runs/connection-check
```

This makes one paid call. Check `runs/connection-check/results.jsonl` for `status: "ok"`. Arrange assistant-history exports now too. Reading and setup are outside the four-hour timer; literature research and experiment design begin the timed work.

## Run your study

Copy any inputs you want to change:

```sh
mkdir -p experiment
cp data/personas.jsonl data/scenarios.jsonl prompts/decision.txt experiment/
```

Edit those copies and create `experiment/trials.jsonl` using the [schema](data/README.md). Pass the copied paths explicitly:

```sh
python3 run.py prepare \
  --trials experiment/trials.jsonl \
  --personas experiment/personas.jsonl \
  --scenarios experiment/scenarios.jsonl \
  --prompt experiment/decision.txt \
  --out runs/pilot-preview

python3 run.py run \
  --trials experiment/trials.jsonl \
  --personas experiment/personas.jsonl \
  --scenarios experiment/scenarios.jsonl \
  --prompt experiment/decision.txt \
  --out runs/pilot
```

Inspect the preview before running. Omitted input flags use the original files under `data/` and `prompts/`. Every trial starts a fresh conversation. Conditions and replicate labels are not shown to the model. The runner preserves the option order in your chosen scenario.

Optional settings: `--env-file PATH` (default `.env`), `--max-calls N` (default 200 per invocation), `--max-completion-tokens N` (2048), `--timeout SECONDS` (60), and `--temperature VALUE` (omitted by default; model support required). The call cap is an accident guard, not your spend allowance. Track usage across all runs.

## Bad replies and HTTP errors

A malformed, truncated, or invalid-choice reply is saved as `invalid_output`; **the next trial still runs**. Such replies are not retried automatically. The manifest reports invalid counts and `completed_with_invalid_outputs` when appropriate. Keep these observations in your accounting.

**HTTP or connection errors stop the batch**, preserving completed attempts. For HTTP 429, wait at least the saved `retry_after_seconds`, or 60 seconds if absent, then retry unfinished trials once if appropriate. You do not need to wait for an interviewer to try this. Repeated 429s may indicate exhausted quota: record the interruption, pause API-dependent work, and notify us asynchronously. HTTP 401/403 requires access to be repaired; do not repeatedly retry.

Export unfinished trials without repeating completed observations:

```sh
python3 run.py remaining --from-run runs/pilot --out experiment/remaining.jsonl
```

If any remain, for the default model/sampling settings:

```sh
python3 run.py run \
  --trials experiment/remaining.jsonl \
  --personas runs/pilot/inputs/personas.jsonl \
  --scenarios runs/pilot/inputs/scenarios.jsonl \
  --prompt runs/pilot/inputs/decision.txt \
  --out runs/pilot-retry
```

Retain the same model and any extra sampling flags you previously chose. Keep both runs. `remaining` includes transport-failed and unattempted trials; it excludes recorded invalid outputs unless you explicitly add `--include-invalid`. Explain any such retries in your analysis. Interrupted calls may already have incurred usage.

Each run needs a new directory. Inputs, requests, responses, settings, and token usage are saved; `.env` is never copied. Saved outputs support reproducible analysis, although live reruns may differ. Prepared requests or stubbed tests are not model evidence.

Optional offline checks: `python3 -m unittest discover -s tests -v`.
