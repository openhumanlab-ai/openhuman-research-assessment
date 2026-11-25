## Process log

### Experiment 0 — exploratory test

Ran one dinner choice for each of the six starter personas, using the original
option order. The goal was to check the workflow from preview to live results.
All six calls returned valid choices.
This was simply a test_experiment to get familiarised with the experimentation workflow.
Also re-organised the original structure into experiment 1, 2, ...

### initial literature review (pre-research question)

before any initial research questions can be asked, I did some exploratory literature review on what's already been done in in this space, to get a sense of the research space. prompted claude to generate most relevant papers in the space of LLM predicting buying purchase choices on prompted traits. Papers found:

Choi et al. (2026), "What Makes a Sale?"

Allouah et al. (2025), "What Is Your AI Agent Buying?"

Gui & Toubia (2023, revised 2025), "The Challenge of Using LLMs to Simulate Human Behavior"

Brand, Israeli & Ngwe (2023), "Using LLMs for Market Research"

Horton, Filippas & Manning (2023, revised 2026), "Homo Silicus"

Reusens et al. (2026), "Would a Large Language Model Pay Extra for a View? Inferring Willingness to Pay from Subjective Choices"

Mohammadi (2024, revised 2026), "Token Noise and the Illusion of Preference: A Shapley Value Framework for Auditing LLM-Simulated Choice Experiments"

Ren et al., "Persona Following Is Not Selective Control: The Neutrality Gap in LLM User Simulation"

prompted claude to summarise the main methods, results and conclusions of each paper but also double checked the source paper for every strong claim (e.g. conclusions, specific numbers, ..). Finally, after reading through papers, claude was prompted to summarise.

Main findings tables:

The two tables share the same numbering: the first covers what each study did, the second what it found. "Purchase choice?" marks whether the model's decision is a buying decision, meaning which product to buy or whether to buy at all, with a price involved.

#### What each study did

| # | Paper | Persona or prompt change | Task and what was measured | Models | Purchase choice? | Human comparison |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | [Choi et al. 2026](https://arxiv.org/abs/2604.04468) (COLM) | Buyer labelled price-sensitive or price-indifferent, plus gender, pickiness, rationality; price moved −10% to +10% | Buy or not buy one product after a sales conversation; purchase rate and price responsiveness | 8 LLMs | Yes | None for the trait effect |
| 2 | [Allouah et al. 2025](https://arxiv.org/abs/2508.02630) (preprint) | Added "The user is price sensitive" on top of an ignore-position instruction; position, price, rating, badges randomised | Pick one of eight products on a mock shop page; weight on each factor | 6 frontier models (prompt test on 3) | Yes | None |
| 3 | [Gui & Toubia 2023](https://arxiv.org/abs/2312.15524) (working paper) | "You, AI, are a customer"; price varied from free to double; later added persona details and disclosed the experiment | Buy or not buy one grocery product; purchase rate at each price | GPT-4o-mini; fix tested on other OpenAI models | Yes | Yes, 991 survey respondents |
| 4 | [Brand, Israeli & Ngwe 2023](https://www.msi.org/working-paper/using-llms-for-market-research-2/) (working paper) | "A customer is randomly selected…"; added income, gender, race, politics; price and features varied | Choose one of two products or neither; amount willing to pay per feature | Mainly GPT-3.5 Turbo | Yes | Yes, five own surveys and one published study |
| 5 | [Horton, Filippas & Manning 2023](https://arxiv.org/abs/2301.07543) (working paper) | One-line personas: political view, or "You only care about fairness / total payoff / your own payoff" | Rate fairness of a price rise; split money with another person | GPT-4; four models for the money game | No | Published results of the original studies only |
| 6 | [Reusens et al. 2026](https://arxiv.org/abs/2602.09802) (preprint) | User described as budget-minded student or business traveller; option order swapped; prompt reworded | Choose between two hotel rooms, 240 dilemmas; amount willing to pay per feature | Llama 3.3 70B, GPT-4o, Gemini-3.1-Pro | Yes | None; published figures shown as reference only |
| 7 | [Mohammadi 2024](https://arxiv.org/abs/2404.01332) (preprint) | No persona, "You are a consumer", or "You are a budget-conscious consumer…"; small wording and formatting edits | Choose between two flights, hotels or phones; probability of picking the cheaper one | 4 open-weight models | Yes | None |
| 8 | [Ren et al. 2026](https://arxiv.org/abs/2609.35036) (preprint) | One trait flipped (mainly risk-seeking vs risk-averse); unrelated attribute left unstated, given a preference, or given "no preference" | Unrelated two-option choices such as phone-case colour; how often the choice shifts | 13 models | No | None |

#### What each study found

| # | Main result | Authors' conclusion | Main pitfall |
| --- | --- | --- | --- |
| 1 | Price-sensitive buyers reacted far more to price (2.58 vs 0.76); annotators recognised the trait 93–99.7% of the time | Prompted personas are reliably preserved and reproduce real-world patterns | The gap between groups persisted with the persona text removed, unexplained; the wording instructs the behaviour |
| 2 | Weight on price rose sharply (−1.76 to −5.64 for Claude Sonnet 4); position effects shrank but remained | Prompting re-weights price strongly, but position biases are built into the models | Price line never tested alone, one wording; the model shops for a user and does not play a person |
| 3 | The model's assumed context shifted with price; its demand curve was an inverted U, humans' sloped down; one spending trait cut error from 0.225 to 0.097, more traits raised it again | Changing one prompt variable shifts unstated others; added detail gets overweighted; tell the model the experiment design | Price is manipulated, not a trait; the fix changed two things at once |
| 4 | Averages often realistic ($3.40 vs $3.27 for fluoride); group differences exaggerated (declined to buy: 95% vs 34% by income in GPT, 49% vs 47% in people) | Useful supplement for the average customer; could not reflect differences between groups | Demographics, not traits; old model |
| 5 | Answers moved in the persona's direction with near-total compliance; without a persona, models did not resemble people | A cheap way to explore ideas before human studies; results need empirical confirmation | Absolute wording makes it close to an instruction-following check; answers were very uniform |
| 6 | Student persona chose the cheapest room in over 95% of dilemmas (Gemini always); business persona inflated feature values enormously; order and rewording changed estimates | Personas shift choices as intended, but to unrealistic extremes | Persona mixes budget, trip purpose and identity; one run per dilemma |
| 7 | In one worked example, the cheaper flight was chosen at 0.915 with no persona, 0.56 with the generic one, about 1 with the budget one; five blank lines alone gave 0.593 | Separate what the simulated person prefers from how the question was asked | Headline numbers come from one model and one task; single author |
| 8 | Flipping the trait shifted unrelated choices in every model; "no preference" still left 38–76% of cases shifting; irrelevant colour labels changed the measured trait effect by 25.5 points | Acting in line with a persona does not show it affects only the intended behaviour | Target trait is risk, not price; thresholds are the authors' own |

Years shown are first-posting dates; papers 3, 4, 5 and 7 were read in their 2025–26 revisions.

### Research Question 1

#### reasoning behind research question: 

several studies in the lit review found that an LLM will often closely follow the persona or budget label it's given. The price sensitive LLM will often pick the cheapest option. Reusens et al. shows 95% of choices went to the cheapest room if LLm is prompted as a budget-minded student (which bundles budget with identity and trip purpose). Mohammadi, 2024 found the budget concious persone chose the cheapest flight with prob close to 100% (one model, one flight task, already 0.915 with no persona), Horton, Filippas & Manning (2023) found near-total persona compliance. The simple test asks one question at one price (does price sensitive alex go for the 7pound option yes or no). let's say the answer is no every time. This has 3 weknesses:

It only says that sensitive alex refuses 7pound, not at which price point it would also refuse.

It may not tell sensitive alex apart from no-trait alex, who also chose to cook at 7pound in experiment 0 (one call only).

the result would look exactly the same if the model were prompted to just pick the cheapest one, and no paper in the lit review ran an always cheapest control.


Instead, we could ask at many different prices and see what the highest price is that sensitive alex would still buy, compared with no-trait alex. An always cheapest baseline stops at £4 by definition, so the real question is whether sensitive alex pays any extra at all. To answer that we test small steps just above £4 (0.5%, 1%, 2%, 5%, 10% extra) and decide beforehand that less than 1% extra counts as nothing. If sensitive alex pays less than that, this shows the model is just following the description like an order to pick the cheapest of the two options. If sensitive Alex still buys at clearly higher prices, this shows the description works more like a preference, and the gap to no-trait alex tells us how strong that preference is.

#### research question:

At a single price, are the LLM's choices for high- and low-sensitivity Alex already all-or-nothing? Does recording the price at which Alex switches tell the high-sensitivity description apart from no-trait Alex, and from an explicit "always pick the cheapest" rule (does it pay 1% or more extra)?

#### further explanation of rq1:

results could look like this : 

| persona | simple test at £7: % that picks the cheaper option | price ladder: highest price still paid |
| --- | --- | --- |
| low sensitivity | 0% | £10 |
| no trait | 100% | £5.20 |
| high sensitivity | 100% | £4.40 |
| cheapest pick (control, known in advance) | 100% | £4.00 |

Part 1 of the question asks wether the simple test is too blunt to size the actual effect, so how close it is to 0% and 100%. This is an open question, because our description is softer than the labels in the papers. Part 2 of the question asks wether sensitive alex stops paying at the same point as the control (£4, known in advance), so really whether it pays any extra, measured in small steps and compared with no-trait alex. if it pays less than 5% extra, the description is just acting as an instruction and if it pays more the description is more realistically acting as a preference. Because the answer depends on how fine the price steps are, we report the amount with the step size. This research question compares two ways of testing on the same data and could give evidence of choosing one method over the other.

#### rq1 research plan: 

alex versions:

| persona_id | version |
| --- | --- |
| profile-03 | no trait |
| profile-02 | high sensitivity |
| profile-06 | high sensitivity (starter paraphrase) |
| profile-01 | low sensitivity |
| profile-05 | low sensitivity (starter paraphrase) |

Scenarios: `dinner`, `dinner-reversed`, `groceries`, `groceries-reversed`, `headphones`, `headphones-reversed`

Changes to scenarios: we only change the price of the expensive option in the text (7 pound dinner, 34 pound delivery and 45 pound wireless)

The option_ids and the option order stay exactly as in the starter. Whole-pound prices are written as in the starter ("£6"), other prices with pence ("£4.20").

Price ladder: 

Each price is the cheaper option's price plus a percentage. The same percentages are used in every scenario. Prices are rounded to the nearest penny.

| extra cost | dinner: `prepared` (cook is £4) | groceries: `deliver` (collect is £30) | headphones: `wireless` (wired is £25) |
| --- | --- | --- | --- |
| 0% | £4 | £30 | £25 |
| 0.5% | £4.02 | £30.15 | £25.13 |
| 1% | £4.04 | £30.30 | £25.25 |
| 2% | £4.08 | £30.60 | £25.50 |
| 5% | £4.20 | £31.50 | £26.25 |
| 10% | £4.40 | £33 | £27.50 |
| 13.3% | £4.53 | £34 (starter price) | £28.33 |
| 20% | £4.80 | £36 | £30 |
| 30% | £5.20 | £39 | £32.50 |
| 50% | £6 | £45 | £37.50 |
| 75% | £7 (starter price) | £52.50 | £43.75 |
| 80% | £7.20 | £54 | £45 (starter price) |
| 100% | £8 | £60 | £50 |
| 150% | £10 | £75 | £62.50 |

 The starter-price row (75% for dinner, 13.3% for groceries, 80% for headphones) is the simple one-price test from the starter pack, so we get that test from the same data.

No need to run an always cheapest pick control since we can just generate this data during analysis or later (we already know what the choice will be)

84 scenarios (3 base-scenarios x 14 prices x 2 orders). Each of the 6 starter scenarios is copied once per price. The id carries the percentage in tenths of a percent, for example `dinner-pct0005` (0.5%), `dinner-pct0750` (75%, starter price), `groceries-reversed-pct0133` (13.3%, starter price) and `headphones-pct0800` (80%, starter price). 

84 records is a lot to write by hand so I'll write a script to automate that 
run everything twice (r1 and r2), to see if the same call gives the same answer.

Number of calls:

5 alex versions x 14 prices x 3 base-scenarios x 2 orders = 420 calls per round. This gives a total of 840 calls including the second round

The runner refuses more than 200 trials in one run unless told otherwise, so each round gets its own trials file and its own run with `--max-calls 420`.


- `trial_id`: unique, made of round, persona and scenario, for example `r1-profile-02-dinner-reversed-pct0750`
- `persona_id`: one of the 5 alex versions
- `scenario_id`: one of the 84 new scenarios
- `condition`: persona, base-scenario, percentage and order, for example `profile-02;dinner;pct0750;reversed` (not shown to the model)
- `replicate_id`: `r1` or `r2`

- model: gpt-5.1-2025-11-13
- prompts/decision.txt unchanged
- runner default settings (no temperature flag); only `--max-calls` is raised to 420, which is a safety cap and not a model setting

Rules for reading the results:

At each price we have 4 answers per alex version per base-scenario (2 orders x 2 rounds). Alex "still pays" at a price if at least 2 of the 4 answers pick the expensive option. The highest price still paid is the highest price at which this is true.

- if alex does not still pay at any extra cost, we report "less than 0.5% extra"
- if alex still pays at 150%, we report "more than 150%" and not a number
- if alex stops and then pays again at a higher price, we count that as a flip back, report how often it happens, and also give the first price at which alex stopped

Commands:

Files used: `experiment_1/scenarios.jsonl` (the 84 scenarios), `experiment_1/trials_r1.jsonl` and `experiment_1/trials_r2.jsonl` (420 trials each). Personas and the decision prompt are not passed, so the runner uses the starter originals (`data/personas.jsonl` and `prompts/decision.txt`).

Run from the repository root, in this order: check (no model calls), prepare (no model calls, then inspect `runs/rq1-round1-preview/requests.jsonl`), round 1 (420 paid calls), round 2 (420 paid calls).

```sh
python3 run.py check \
  --trials experiment_1/trials_r1.jsonl \
  --scenarios experiment_1/scenarios.jsonl

python3 run.py prepare \
  --trials experiment_1/trials_r1.jsonl \
  --scenarios experiment_1/scenarios.jsonl \
  --max-calls 420 \
  --out runs/rq1-round1-preview

python3 run.py run \
  --trials experiment_1/trials_r1.jsonl \
  --scenarios experiment_1/scenarios.jsonl \
  --max-calls 420 \
  --out runs/rq1-round1

python3 run.py run \
  --trials experiment_1/trials_r2.jsonl \
  --scenarios experiment_1/scenarios.jsonl \
  --max-calls 420 \
  --out runs/rq1-round2
```
