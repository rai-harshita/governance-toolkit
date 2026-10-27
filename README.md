# AequiGate

**Responsible AI Equity Monitoring and Model Governance Toolkit**
*Evidence before deployment.*

AequiGate is a pre-release checkpoint for AI systems. It tests a system for unfair outcomes, unstable or proxy-driven explanations, and generative-AI safety failures. It then maps every result to a release decision (PASS, CONDITIONAL, BLOCK or HUMAN REVIEW) and requires a named human reviewer to approve release. Principles such as "be fair" and "be safe" become repeatable, reviewable evidence.

## What it does

| Stage | What happens | Where |
|---|---|---|
| Define | Governance schema; 25 documented normal, edge and incomplete test cases with assumptions and acceptance criteria | `schema/`, `data/test_cases.yaml` |
| Test | Fairness, explainability and GenAI safety checks, each compared with a simple baseline | `checks/` |
| Decide | Config-driven rules turn metrics into a decision with reasons and corrective actions | `decision_engine.py`, `configs/rules.yaml` |
| Review | Dashboard with risk register, release gate, human-review states and a hash-chained audit log | `dashboard/app.py` |

### Systems audited

1. **Adult Income Classifier** (tabular). Baseline: logistic regression. Selected: gradient boosting. Mitigations: threshold optimisation for demographic parity and for equalised odds.
2. **College Helpdesk Chatbot** (generative AI). Baseline: plain system prompt. Hardened: strict rules plus input and output filters. Tested with 24 main, 10 held-out and 6 Hindi/Punjabi prompts, repeated 3 times.

### Features

- Fairness: demographic parity, equal opportunity, equalised odds, disparate impact (80% rule), bootstrap 95% intervals, sex, race, age group and sex x race intersections, counterfactual sex-flip test
- Explainability: SHAP, permutation-importance baseline, stability score, proxy-feature detection
- GenAI safety: injection, jailbreak, PII leakage, bias, hallucination, over-refusal, held-out and multilingual splits, refusal quality
- Governance: rules in YAML, policy mapping (NIST AI RMF, EU AI Act, India AI governance principles), risk register, release gate, tamper-evident audit log, role-based login, PDF audit report
- Audit a System: upload a predictions CSV or a chatbot system prompt and receive a decision under the same rules

## Installation

Requires Python 3.12 (3.15 is too new for several dependencies).

```powershell
git clone https://github.com/rai-harshita/governance-toolkit.git
cd governance-toolkit
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Create a `.env` file in the project root with a free Groq key (never commit it):

```
GROQ_API_KEY=your_key_here
```

## Run

```powershell
python run_all.py                       # runs all checks, writes evidence/latest.json (about 15 minutes)
python -m checks.auth <user> <password> admin "Full Name"    # create an admin account
python -m streamlit run dashboard/app.py
```

Sign up on the login page for a Submitter account. Reviewer and admin accounts are created only with the `checks.auth` command above.

| Role | Access |
|---|---|
| Submitter | Overview and Audit a System, own systems only |
| Reviewer | All evidence pages, release gate, policy mapping |
| Admin | Everything |

## Reproduce the results

- Tabular results are deterministic: split seed 42, fixed model seeds, 200 fixed-seed bootstrap resamples.
- GenAI results depend on the model and vary between runs even at temperature 0. The run reported here used `qwen/qwen3.8-27b` with 3 repeats (240 calls, 0 API errors). Earlier models (llama, gpt-oss) gave different numbers; one was abandoned when its daily token quota ran out, and its figures are not reported.
- Run the tests: `python -m pytest -q` (49 tests, offline, about one minute).

## Headline findings

| Finding | Value |
|---|---|
| Disparate impact ratio, selected model, by sex | 0.31 (standard: 0.80) |
| Removing the sex column | DP gap 0.177 to 0.169; proxies carry the signal |
| DP mitigation | DP gap 0.177 to 0.013, but EO gap 0.095 to 0.330 |
| EO mitigation | EO gap 0.017, DP gap 0.099, accuracy cost 1.2 points |
| Counterfactual sex flip | 2.5% of decisions change (7.9% for the baseline) |
| Classifier decision | BLOCK |
| Chatbot baseline vs hardened, injection | 50% vs 0% successful attacks (n=24) |
| Chatbot decision | PASS |

## Project structure

```
schema/            governance record (Pydantic)
data/              test cases, GenAI prompt suite
checks/            fairness, explainability, GenAI safety, extended metrics,
                   audit chain, auth, policy map, PDF report, upload audit
configs/rules.yaml thresholds that drive every decision
decision_engine.py rule engine
run_all.py         one-command pipeline
dashboard/app.py   Streamlit app
theme.py, login_page.py   presentation layer
tests/             pytest suite
evidence/          generated results (latest.json is committed)
```

## Assumptions

- Adult dataset: 30% test split, positive class is income above $50K.
- Thresholds in `configs/rules.yaml` are policy choices. The 0.80 disparate-impact limit is a common screening threshold from US employment guidance, not a legal verdict.
- Uploaded audits judge the supplied labels and predictions as given.

## Limitations

- The Adult data is from the 1994 census; this is a demonstration, not a deployable lending or hiring model.
- Bootstrap intervals reflect test-set sampling only, not retraining variance, and are conservative for gaps near zero.
- GenAI scoring is keyword-based and the prompt suite is small. "No successes observed in 24 trials" is not zero risk; the true rate could still be about 12%.
- Results depend on the model and vary between runs.
- Stability was tested only with small numeric noise on 300 rows.
- Uploaded tabular audits cannot run SHAP or counterfactual tests, because they do not include the model.
- The age gap may partly reflect legitimate career-stage differences and needs human justification.
- The login is demonstration-grade: salted scrypt hashes and role-based pages, but no rate limiting, password reset or single sign-on.
- The hash chain detects edits but does not prevent a person with file access from rewriting the whole chain.
- Policy-clause mappings are the project's interpretation and should be checked against the published texts.

## Responsible use

AequiGate supports human judgment and does not replace it. A system is released only when it is not BLOCKED and a named reviewer has approved it. Uploaded rows are never stored, only aggregate results.