# OpenHuman — research work sample

**How should we test whether an assigned persona trait influences an LLM's decisions?**

OpenHuman uses simulated customer populations to compare products, offers, and experiences. One assumption behind this approach is that a persona's assigned characteristics meaningfully influence its choices.

Focus on **price sensitivity**: the tendency to give monetary cost greater weight in purchase trade-offs. You may refine this working definition with a reason.

Review relevant research, recommend an evaluation, and run a small pilot. Give us a recommendation supported by the evidence you found and generated.

## Start here

```sh
git clone https://github.com/openhumanlab-ai/openhuman-research-assessment.git
cd openhuman-research-assessment
```

Read this brief, then follow [SETUP.md](SETUP.md) for the Python runner and access check. The [data guide](data/README.md) explains the inputs. [SUBMISSION.md](SUBMISSION.md) lists what to return, and the [AI-history guide](ai-history/README.md) explains what to save from the start.

## Before the timer

**Reading this pack and its example data, setup, the one-call connection check, and arranging AI-history exports are outside the four-hour limit.** Complete those first; see [SETUP.md](SETUP.md). We provide API access, a permitted model, and a spend allowance. You are not expected to pay for access.

Start the timer when you begin literature research or experiment design after onboarding. Literature reading, design, model experiments, analysis, and writing are inside the **four-hour active-work limit**. Stop at the limit and describe unfinished work. Pause for supplied-infrastructure failures. Final file export/upload is outside the timer; do not add research or analysis during that step.

## Materials

- Six synthetic descriptions of **one fictional person**, not six sampled customers.
- Three purchasing scenarios, each in two opposite option orders: six scenario records.
- A Python runner that saves each trial's exact prompts, responses, and settings.

These are examples, not a validated instrument or human-choice dataset. You may use a subset, adapt copies, or create alternatives. Preserve the originals and explain consequential changes. The [data notes](data/README.md) describe formats and identifiers.

## The work

1. **Frame a narrow question.** State a testable claim and what evidence would change your view.
2. **Review relevant research.** Explain how you searched, why key sources matter, what they actually tested, their limitations, and what the evidence collectively supports. A few carefully examined sources are enough; there is no paper-count target.
3. **Design an evaluation.** Explain your comparisons, measurements, and interpretation. Save a short plan before the main pilot; record significant later changes.
4. **Run a small pilot.** Use one trait and one primary model within the supplied allowance. Keep the evidence needed to inspect the results.
5. **Recommend a next step.** Distinguish published evidence, pilot findings, and your judgment. Explain uncertainty and the most useful next experiment.

A small, negative, or inconclusive result is acceptable. You do not need every supplied example, a positive effect, or a production system. No frontend, deployment, or model training is required.

## Working together

Treat Ram and Alessandro as coworkers: ask clarifying questions, validate assumptions, and discuss trade-offs. If unavailable, proceed with reasonable recorded assumptions.

AI tools are allowed. You own the source checks, method, code, and conclusions. **Save your prompting history from the start:** your prompts, visible assistant responses, and follow-up instructions for research and coding. Also retain experimental model prompts and outputs. See [ai-history/README.md](ai-history/README.md).

## Submission and assessment

Submit one concise research note with supporting files, as described in [SUBMISSION.md](SUBMISSION.md). The plan and process details can live in the same note or notebook; separate reports are unnecessary.

| Dimension | Points |
| --- | ---: |
| Literature search, critical reading, synthesis | 30 |
| Research question and evaluation design | 25 |
| Interpretation and recommendation | 20 |
| Pilot execution and reproducibility | 15 |
| Collaboration, prioritisation, AI ownership | 10 |

We assess reasoning and evidence, not paper count, prompt count, or code volume. There is no hidden preferred method or expected result.
