# Scoring Model

Status: **specified, implemented in `backend/app/engine/`, not yet run.** The worked example below was calculated by hand. The tests in `backend/tests/engine/` encode it, and it counts as confirmed only after you run the tests and share the output (see `docs/TESTING.md`, section 7).

This is the weighted-sum model with min-max normalization. It is a standard technique. It is not new, and it does not find an objectively correct answer. It makes the trade-offs you entered visible and repeatable.

## 1. Inputs

- Options `o = 1..n` (at least 2, at most 20).
- Criteria `c = 1..m` (at least 1, at most 15). Each criterion has:
  - a direction: **benefit** (higher is better) or **cost** (lower is better),
  - a raw weight `r_c` between 0 and 1000,
  - an optional unit label (display only; the engine never converts units).
- A value `x[o][c]` for every option on every criterion. **Every cell must be filled.** Missing values are rejected, never treated as zero (D-005 in `docs/DECISIONS.md`).
- Optional hard constraints: `criterion <= threshold` or `criterion >= threshold`, tested on the raw value. A value exactly equal to the threshold passes.

All numbers must be finite and have absolute value at most 1e12. All values of one criterion must share one unit; the engine cannot check this.

## 2. Steps

### Step 1: Weights

`w_c = r_c / sum(r)`. The weights then sum to 1. Multiplying every raw weight by the same factor changes nothing (scale invariance). A weight of 0 is allowed and makes that criterion irrelevant to the score. If all raw weights are 0, the model is rejected.

### Step 2: Eligibility (hard constraints)

An option that breaks any constraint is **ineligible**. Every violated rule is recorded with a plain-language reason. Ineligible options get no score and no rank, but they stay in the result so the user sees why they were excluded. A high score can never make an ineligible option look feasible, because it never receives one.

### Step 3: Normalization (eligible options only)

For each criterion, take the minimum and maximum raw value among the **eligible** options only (D-002).

- benefit: `n = (x - min) / (max - min)`
- cost: `n = (max - x) / (max - min)`

Every `n` lies between 0 (worst eligible option) and 1 (best eligible option). If `max == min`, the criterion cannot separate the options, so every eligible option gets `n = 0.5` (D-004). This is a neutral value, not a claim that the options are "half good".

### Step 4: Score, contributions, rank

- Contribution of criterion `c` to option `o`: `w_c * n[o][c]`.
- Score: the sum of that option's contributions, so contributions add up to the score exactly. Scores lie between 0 and 1.
- Rank: descending score. Scores within `1e-9` of the first score in a group are a **tie** and share a rank ("1, 1, 3" numbering). Tied options keep the order the user entered them, so output order is stable. A tie for first place is flagged.

### Step 5: Explanation

Plain-language text is produced from templates filled with the real numbers: the leader, its largest contributions, the margin over the runner-up, ties, and the reason each ineligible option was excluded. No AI is involved.

## 3. Worked example

Choose a laptop.

| Option | Price (cost) | Quality rating (benefit) |
|---|---|---|
| A | 800 | 7 |
| B | 1000 | 9 |
| C | 600 | 5 |

Raw weights: price 4, quality 6, so `w = 0.4` and `0.6`. No constraints.

Price is a cost, min 600, max 1000: A = (1000-800)/400 = 0.5, B = 0, C = 1.
Quality is a benefit, min 5, max 9: A = (7-5)/4 = 0.5, B = 1, C = 0.

| Option | Price contribution | Quality contribution | Score |
|---|---|---|---|
| A | 0.4 x 0.5 = 0.20 | 0.6 x 0.5 = 0.30 | 0.50 |
| B | 0.4 x 0 = 0.00 | 0.6 x 1 = 0.60 | 0.60 |
| C | 0.4 x 1 = 0.40 | 0.6 x 0 = 0.00 | 0.40 |

Ranking: B (0.6), A (0.5), C (0.4).

**With constraint `price <= 900`:** B is ineligible (1000 > 900). Normalizing over A and C only: price range 600 to 800 gives A = 0, C = 1; quality range 5 to 7 gives A = 1, C = 0. Scores: A = 0.4 x 0 + 0.6 x 1 = 0.6, C = 0.4 x 1 + 0.6 x 0 = 0.4. Ranking: A, C. B is listed as excluded.

**Equal weights (0.5 each):** every option scores 0.5, so all three tie for first.

## 4. Limitations (also shown in the product)

- **Scores are relative to the options entered.** Adding, removing, or excluding an option can change the scores and sometimes the order of the others (rank reversal). Toggling a constraint changes the scale for the remaining options, because normalization uses eligible options only.
- **One extreme value compresses the rest** on that criterion.
- **Linear trade-offs.** More of a benefit is always proportionally better, and criteria can be traded against each other. Criteria with a best value in the middle are not supported yet.
- **Weights and ratings are judgments.** The model shows what follows from them. It cannot say whether they are right.
- **A narrow win is not a clear win.** Use the sensitivity analysis (later phase) before treating the top option as clearly best.
- It does not predict the future, and its scores are not probabilities.
