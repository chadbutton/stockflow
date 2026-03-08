# Setup: UnR (Undercut and Run) — Gil Morales + The Strat

This document defines the **first setup**: UnR (Undercut and Run), based on Gil Morales’ OWL methodology (undercut of a moving average) with a **65-minute** trigger using **The Strat** reversal pattern (Rob Smith). Each trigger receives a **score out of 100** from historical performance of the same pattern.

---

## 1. Source Concepts

- **Gil Morales (OWL):** Moving Average Undercut & Rally (MA U&R). Price undercuts a key moving average then rallies back above it; we use **20, 50, and 200 exponential moving averages** on the **daily** chart.
- **The Strat (Rob Smith):** Three bar scenarios — **1** = inside bar, **2** = one-side (2U = break high only, 2D = break low only), **3** = outside bar. Reversal patterns such as **2-1-2** (directional → inside → opposite directional) define the **exact trigger** on the 65-min chart.

---

## 2. Daily Chart Context (UnR)

### 2.1 Moving Averages

- **EMAs:** 20, 50, 200 (exponential moving average).
- All computed on **daily** OHLC (typically close).

### 2.2 Bullish UnR (Long Setup)

- **Which MA:** Price has **undercut** one of the three EMAs (20, 50, or 200). “Undercut” = price trades below the MA then closes back above it (or we require a touch/undercut in the last 3–5 days).
- **Price action:** Price has been **falling for 3–5 days** into that MA (pullback).
- **MA slope:** The MA that was undercut must be **upsloping** (e.g. EMA today > EMA 5 days ago).
- **Result:** We have a valid **bullish UnR context** when: (1) in the last 3–5 days price declined, (2) price undercut one of 20/50/200 EMA, (3) that EMA is upsloping. The **trigger** then comes from the 65-min Strat reversal.

### 2.3 Bearish UnR (Short Setup)

- **Which MA:** Price has **undercut** one of the three EMAs from above (i.e. price was above MA, came down, went below MA, then back above; for short we use the inverse: price rallies up to a **downsloping** MA).
- **Price action:** Price has been **rising for 3–5 days** up to that MA.
- **MA slope:** The MA that price is testing must be **downsloping** (e.g. EMA today < EMA 5 days ago).
- **Result:** Valid **bearish UnR context** when: (1) in the last 3–5 days price advanced, (2) price tests or undercuts one of 20/50/200 EMA from below, (3) that EMA is downsloping. Trigger = 65-min Strat reversal (bearish 2-1-2).

### 2.4 Which MA “Counts”

- We evaluate **all three** (20, 50, 200). A symbol can qualify on **20 only**, **50 only**, **200 only**, or more than one. Each is a **separate setup instance** for scoring (e.g. “UnR 20 EMA” vs “UnR 50 EMA”).
- Stored with each trigger: **ma_used** = 20 | 50 | 200.

---

## 3. Trigger: 65-Minute The Strat Reversal (All Patterns)

### 3.1 Bar Classification (The Strat)

Each 65-min bar is classified relative to the **previous** bar:

| Type | Name    | Rule |
|------|---------|------|
| **1** | Inside  | High &lt; prev high AND Low &gt; prev low (range inside previous bar). |
| **2U** | Two-up  | Breaks previous **high** only (high &gt; prev high, low ≥ prev low). |
| **2D** | Two-down | Breaks previous **low** only (low &lt; prev low, high ≤ prev high). |
| **3** | Outside | Breaks both (high &gt; prev high AND low &lt; prev low). |

Candle color is **ignored** for 1/2/3; only high/low vs previous high/low matter.

### 3.2 Reversal Patterns Used (Configurable)

The trigger accepts **all** Strat reversal patterns. They are tried in order; the **first match** wins. Configure via **strat_reversal_patterns** in setup criteria (default: 2-1-2, 2-2, 1-2-2, 3-1-2, 1-3).

| Pattern | Structure | Bullish | Bearish |
|---------|-----------|---------|---------|
| **2-1-2** | 4 bars: directional → inside → opposite | 2D → 1 → 2U (break inside high) | 2U → 1 → 2D (break inside low) |
| **2-2** | 3 bars: two opposite directionals | 2D → 2U (break 2D high) | 2U → 2D (break 2U low) |
| **1-2-2** | 4 bars: inside → directional → opposite | 1 → 2D → 2U | 1 → 2U → 2D |
| **3-1-2** | 4 bars: outside → inside → directional | 3 → 1 → 2U | 3 → 1 → 2D |
| **1-3** | 3 bars: inside → outside (broadening) | 1 → 3, close &gt; mid(inside) | 1 → 3, close &lt; mid(inside) |

Entry = close of trigger bar (the bar that confirms the break). Stop = opposite side of the key bar (inside bar for 2-1-2/3-1-2, first bar for 2-2, second bar for 1-2-2, outside bar for 1-3).

### 3.3 Stored with Trigger

**entry_price**, **stop_price**, **direction** (long/short), **ma_used** (20/50/200), **strat_pattern** (e.g. "2-2", "1-2-2") so scoring can be per pattern.

---

## 4. Full UnR + Strat Logic (Summary)

1. **Daily:** Compute 20/50/200 EMA. For each of 20, 50, 200:
   - **Long:** Last 3–5 days price declined, price undercut this EMA, this EMA is upsloping → bullish UnR context for that MA.
   - **Short:** Last 3–5 days price advanced, price tested/undercut this EMA, this EMA is downsloping → bearish UnR context for that MA.
2. **65-min:** On each new completed bar, try each configured Strat reversal pattern in order. If any pattern matches in the **same direction** as the daily UnR (bullish UnR → bullish reversal, bearish UnR → bearish reversal), then **trigger**; store the pattern name (e.g. "2-2", "1-2-2").
3. **Output:** Symbol, direction, ma_used (20/50/200), entry_price, stop_price, strat_pattern, trigger_time, and **score** (0–100).

---

## 5. Score / Rank (0–100) from Historical Triggers

- **Idea:** Score = how well “the same pattern” has performed in the past.
- **Same pattern:** Same setup_id (UnR), same **ma_used** (20, 50, or 200), same **direction** (long/short), and optionally same **strat_pattern** (e.g. "2-2", "1-2-2") so you can score each reversal type separately.
- **Data:** Every trigger is **stored** in a database (see DB schema below). When we have **resolved** outcomes (e.g. from backtest or from live trade tracking), we can compute:
  - Win rate (%), average R-multiple, number of samples.
- **Score formula (example):**  
  - Base: historical win rate (0–100 scale).  
  - Adjust for sample size (e.g. few samples → pull toward 50).  
  - Optional: blend in average R (e.g. win rate × (1 + avg R) capped at 100).  
  - **Output:** Integer 0–100.
- **When no history:** New pattern (e.g. no prior UnR 200 long) → score = 50 (neutral) or “N/A” until minimum sample size (e.g. 5) is reached.

---

## 6. Database: Storing Triggers for Metric Analysis

All triggers are persisted so we can:
- Compute score from “same pattern” history.
- Analyze by symbol, MA, direction, date.

### 6.1 Suggested Tables

**triggered_setups**

| Column        | Type      | Description |
|---------------|-----------|-------------|
| id            | PK        | Unique id. |
| setup_id      | string    | e.g. `unr`. |
| symbol        | string    | Ticker. |
| direction     | string    | `long` \| `short`. |
| ma_used       | int       | 20 \| 50 \| 200. |
| trigger_time  | datetime  | Bar close time (65-min). |
| entry_price   | decimal   | Entry level. |
| stop_price    | decimal   | Stop level. |
| timeframe     | string    | e.g. `65min`. |
| strat_pattern | string    | e.g. `2-1-2`. |
| created_at    | datetime  | Record creation. |

**resolved_trades** (optional; for scoring from outcomes)

| Column       | Type    | Description |
|--------------|---------|-------------|
| id           | PK      | |
| triggered_setup_id | FK | Links to triggered_setups. |
| exit_time    | datetime | |
| exit_price   | decimal  | |
| r_multiple   | decimal  | P&amp;L in R (e.g. 1.5 = 1.5R). |
| outcome      | string   | e.g. `win` \| `loss` \| `breakeven`. |

- **Score** can be computed on read from `triggered_setups` + `resolved_trades` (or from aggregated stats table), and cached per (setup_id, ma_used, direction) if needed.

---

## 7. Component Boundary and Unit Tests

The UnR + Strat logic lives in a **separate component** with **unit tests** to verify behavior.

### 7.1 Responsibilities

- **Strat:** Classify bar as 1 / 2U / 2D / 3; detect 2-1-2 reversal (bullish/bearish) on 65-min bars.
- **UnR daily:** EMAs 20/50/200; detect 3–5 day move and slope; determine “bullish UnR context” or “bearish UnR context” per MA.
- **UnR evaluator:** Given daily context + 65-min bars, return whether trigger fires and entry/stop.
- **Persistence:** Save trigger to DB; load history for (setup_id, ma_used, direction).
- **Scoring:** From historical triggers + resolved outcomes, compute score 0–100; return 50 or N/A when insufficient data.

### 7.2 Unit Tests (Summary)

- **Strat:**  
  - Classify sequences of (high, low) into 1, 2U, 2D, 3.  
  - Given 3 bars, detect bullish 2-1-2 and bearish 2-1-2; reject invalid sequences (e.g. 2U breaks low → not 2U).
- **UnR daily:**  
  - Given daily OHLC, EMAs slope and 3–5 day decline/rise and undercut logic; one test bullish UnR on 20 EMA, one bearish on 50 EMA, etc.
- **UnR evaluator:**  
  - Mock daily context + 65-min bars; expect trigger when 2-1-2 aligns with context; expect no trigger when context missing or pattern wrong.
- **Scoring:**  
  - Given a list of resolved trades (win/loss, R), assert score is in 0–100 and increases with win rate / R; assert low sample size → 50 or N/A.

This keeps the UnR setup well-defined, implementable, and testable independently of the rest of the platform.
