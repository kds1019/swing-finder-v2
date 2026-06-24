# SwingFinder Scanner — How Stocks Are Scored & Ranked

## Overview

Every scan runs in **two phases**:

1. **Filter Phase** — Hard pass/fail rules eliminate stocks that don't meet minimum criteria.
2. **Scoring Phase** — Every stock that passes is scored 0–100 (SmartScore), then sorted best-first.

Results are split into **Confirmed Setups** (clear Breakout or Pullback) and **Near Misses** (close but not quite).

---

## Phase 1 — Filter Gate (`passes_filters`)

A stock must pass ALL of the following or it is dropped entirely:

| Filter | Condition |
|---|---|
| Price range | Between your Price Min and Price Max sliders |
| Volume | Above your Min Volume slider |
| RSI (Breakout mode) | RSI ≥ 50 |
| RSI (Pullback mode) | RSI ≤ 55 |
| Uptrend gate | EMA20 > EMA50 (both modes) |

If any one of these fails the stock never appears — not even as a Near Miss.

---

## Phase 2 — Setup Classification (`classify_setup`)

Stocks that pass the filter are classified into one of three setups:

| Setup | Rules |
|---|---|
| **Breakout** | EMA20 > EMA50 AND RSI ≥ 55 |
| **Pullback** | EMA20 > EMA50 AND 35 ≤ RSI ≤ 54 AND price ≤ EMA20 |
| **Neutral** | Everything else (shown as Near Miss only) |

---

## Phase 3 — SmartScore Calculation (0–100)

Every confirmed stock starts at a **baseline of 50** and points are added or subtracted:

### A. Setup Strength — up to +40 pts

**Breakout:**
- `(RSI − 50) × 1.2` capped at +25 → rewards stronger RSI momentum
- `(BandPos20 − 0.5) × 50` capped at +15 → rewards price near top of 20-day range

**Pullback:**
- `(60 − RSI) × 1.2` capped at +25 → rewards deeper, cleaner dips
- `(0.5 − BandPos20) × 50` capped at +15 → rewards price near bottom of range

### B. EMA Trend — ±10 pts

| Condition | Points |
|---|---|
| EMA20 > EMA50 (uptrend) | +10 |
| EMA20 < EMA50 (downtrend) | −10 |

### C. Relative Volume — ±15 pts

| Relative Volume vs 20-day avg | Points |
|---|---|
| ≥ 1.5× (high conviction) | +15 |
| 1.0–1.5× (above average) | +5 |
| < 0.8× (weak conviction) | −10 |

### D. Structural Context — up to +12 pts

**Base Detection (Breakouts only):**
Checks if the 3–15 bars before today formed a tight consolidation
(daily range < 3% of price for at least 5 of those bars).

| Condition | Points |
|---|---|
| Breakout from a confirmed base | +12 |

**Meaningful Level (Pullbacks only):**
Checks if price is pulling back to a real support level.

| Condition | Points |
|---|---|
| Within 2% of EMA20 | +10 |
| Within 2% of EMA50 | +8 |
| Within 2% of a pivot low | +8 |

### E. Fibonacci Zone — ±15 pts

Uses the most recent swing high/low (last 20 bars) to calculate retracement:

| Price Position | Zone | Points |
|---|---|---|
| ≤ 38.2% retracement | Deep Discount | +15 |
| 38.2–50% retracement | Discount | +10 |
| 61.8–78.6% retracement | Premium | −10 |
| ≥ 78.6% retracement | Extended Premium | −15 |

**Score is clamped to 0–100 after each step.**

---

## SmartScore Reference Table

| Score Range | Rating | What it means |
|---|---|---|
| 80–100 | 🟢 Excellent | Strong RSI, uptrend, high volume, discount Fibonacci entry, base breakout |
| 65–79 | 🟡 Good | Most criteria met, one or two weaker signals |
| 50–64 | 🟠 Neutral | Baseline setup, no strong tailwinds or headwinds |
| Below 50 | 🔴 Weak | Volume, trend, or Fibonacci working against the setup |

---

## Phase 4 — Fundamental Score (Post-Scan, 0–100)

After the scan completes, a separate fundamental quality score is fetched for each result.
**Source:** Tiingo (DOW 30 tickers) or Yahoo Finance (all others — automatic fallback).

| Metric | Max Points | What earns them |
|---|---|---|
| Profit Margin | 30 pts | >20% = 30, >10% = 20, >0% = 10 |
| Debt / Equity | 25 pts | <0.3 = 25, <0.7 = 15, <1.5 = 5 |
| Current Ratio | 20 pts | >2.0 = 20, >1.0 = 10 |
| Return on Equity | 25 pts | >20% = 25, >15% = 15, >10% = 10 |

**Grade scale:** A ≥ 80 · B ≥ 70 · C ≥ 60 · D ≥ 50 · F < 50

The fundamental score is displayed as a badge on each result card but does **not** change the SmartScore sort order. It is extra context for deciding between setups with similar SmartScores.

---

## Final Sort Order

Results are sorted **descending by SmartScore**.
Ties broken by the order stocks completed scanning (roughly alphabetical).

**Confirmed Setups** (Breakout or Pullback) appear first.
**Near Misses** (Neutral or borderline) appear in a separate section below.

---

## Maximum Possible SmartScore Breakdown

| Component | Max contribution |
|---|---|
| Baseline | 50 |
| Setup strength (RSI + Band) | +40 |
| EMA uptrend | +10 |
| High relative volume | +15 |
| Base detection | +12 |
| Meaningful level | +10 |
| Fibonacci discount | +15 |
| **Raw total before clamp** | **152** |
| **After 0–100 clamp** | **100** |

A score of 100 means the stock hit every positive signal simultaneously.
A score near 50 means it's a valid setup with no strong positive or negative adjustments.
