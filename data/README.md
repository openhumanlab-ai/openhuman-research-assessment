# Data and runner format

All examples are fictional. There are no customer records, observed human choices, or correct-choice labels. Origin and file hashes are in `provenance.json`.

## Inputs

`personas.jsonl` contains six versions of the same fictional Alex, with fields `persona_id` and `text`. Shared wording holds affordability and background constant. The descriptions are not independent people or a validated trait scale. You may select, adapt, or replace them; preserve the originals.

`scenarios.jsonl` contains three situations in both option orders:

| Situation | Original order | Opposite order |
| --- | --- | --- |
| Dinner | `dinner` | `dinner-reversed` |
| Groceries | `groceries` | `groceries-reversed` |
| Headphones | `headphones` | `headphones-reversed` |

Each record has `scenario_id`, `context`, and an ordered `options` list containing `option_id` and `text`. Within a pair, the context, option IDs, and option wording are identical; only display order changes. These are three situations, not six independent items. The runner uses the supplied order without shuffling it. You decide which records and comparisons your study uses.

## Trials

One JSON object per intended request:

```json
{"trial_id":"pilot-001","persona_id":"profile-01","scenario_id":"dinner","condition":"my-condition","replicate_id":"r1"}
```

All fields are required. IDs refer to input records; `persona_id: null` sends no description. `trial_id` must be unique in the file, as must each persona/scenario/condition/replicate combination.

`condition` and `replicate_id` are analysis labels, not model instructions. Changing a label alone changes no treatment. The default one-row `examples/smoke_trials.jsonl` only checks access and format.

## Prompts and results

`prompts/decision.txt` is an editable system prompt. The user message supplies the description, situation, and options. Expected model output:

```json
{"choice_id":"a-listed-option-id","explanation":"A short explanation."}
```

The explanation is generated text, not access to hidden reasoning. The runner checks format and valid option IDs; you decide what the evidence means.

Every run saves `manifest.json`, input/code snapshots under `inputs/`, and exact request bodies in `requests.jsonl`. Live runs also save `results.jsonl`, including raw responses where available. Authentication headers are excluded.

Bad outputs are recorded and the batch continues; HTTP/connection errors stop it. A keyboard interruption records an unknown outcome. A forced kill may prevent the last write: reconcile attempts against the manifest and planned requests. See [SETUP.md](../SETUP.md) for recovery. Live reruns may differ; use saved outputs to reproduce the analysis.
