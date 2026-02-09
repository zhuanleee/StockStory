# Practical Volatility Trading Strategies: A Comprehensive Framework

## Table of Contents
1. [Gamma Scalping -- Complete Framework](#1-gamma-scalping--complete-framework)
2. [Variance Trading](#2-variance-trading)
3. [Dispersion Trading](#3-dispersion-trading)
4. [Volatility Arbitrage](#4-volatility-arbitrage)
5. [Term Structure Trading](#5-term-structure-trading)
6. [Skew Trading](#6-skew-trading)
7. [Earnings Volatility Strategies](#7-earnings-volatility-strategies)
8. [Tail Risk Strategies](#8-tail-risk-strategies)
9. [Regime-Based Volatility Strategies](#9-regime-based-volatility-strategies)
10. [Position Management and Adjustment](#10-position-management-and-adjustment)

---

## 1. GAMMA SCALPING -- COMPLETE FRAMEWORK

### 1.1 The Core Strategy

Gamma scalping (also called delta-neutral trading) is the strategy of buying options (acquiring long gamma), then continuously delta-hedging the resulting position. The trader profits from the mechanical process of rebalancing: buying low and selling high as the underlying oscillates.

**The Setup:**
- Buy ATM straddle (or strangle) to get long gamma
- Delta-hedge with the underlying (stock, futures, or perps)
- As the underlying moves, delta changes -- rebalance to zero delta
- Each rebalance "locks in" a small P&L from the realized move
- At expiry: compare total locked-in rebalancing profits vs. total theta paid

### 1.2 The P&L Formula

The instantaneous P&L for a delta-hedged option position is:

```
dP&L = (1/2) * Gamma * S^2 * (sigma_realized^2 - sigma_implied^2) * dt
```

Where:
- **Gamma**: the second derivative of option price w.r.t. underlying
- **S**: underlying price
- **sigma_realized**: actual (realized) volatility of the underlying
- **sigma_implied**: implied volatility at which the option was purchased
- **dt**: the time increment

**The critical insight**: Gamma scalping is profitable if and only if realized volatility exceeds implied volatility. Implied vol is the "rent" you pay (theta), and realized vol is what you "harvest" through rebalancing.

### 1.3 Step-by-Step Example

**Scenario: Buy ATM straddle at 25% IV on a $100 stock**

1. **Day 1**: Buy ATM straddle (100-strike call + 100-strike put). Position is delta-neutral. Premium paid = $7.50 (combined). Daily theta ~$0.25.

2. **Stock moves +2% to $102**:
   - The call delta increases (e.g., from 0.50 to 0.60), put delta changes (from -0.50 to -0.40)
   - Net delta = +0.20 (position is now long)
   - Sell 20 shares of stock at $102 to neutralize delta
   - This "locks in" a small profit from the $2 move

3. **Stock reverses -1.5% to $100.47**:
   - Net delta shifts negative
   - Buy back some shares at $100.47
   - Again lock in a small profit (bought low after selling high)

4. **Repeat**: Each oscillation generates a rebalancing profit

5. **At expiry**:
   - Total rebalancing profits = sum of all "buy low, sell high" trades
   - Total theta cost = daily theta * days held
   - **Net P&L = Rebalancing profits - Theta cost**
   - If realized vol was ~30% (> 25% implied), you profit
   - If realized vol was ~20% (< 25% implied), theta bleeds exceed scalping gains

### 1.4 When Gamma Scalping Works vs. Fails

**Works when:**
- Realized vol consistently exceeds implied vol (IV is underpriced)
- The underlying exhibits frequent, sizable oscillations
- Mean-reverting price action (buy-dip/sell-rally mechanics thrive)
- High-gamma environments (near ATM, near expiry)

**Fails when:**
- Stock does not move enough; theta bleeds the position dry
- Realized vol < implied vol persistently
- Trending markets (one-directional moves do not generate rebalancing opportunities as efficiently)
- Transaction costs erode the small per-trade gains
- Bid-ask slippage on rebalancing trades

### 1.5 Optimal Rehedging Frequency

The fundamental tradeoff:
- **Too frequent**: Transaction costs (commissions + spread) consume gains. With 50-100 hedge adjustments over 3 days at $5/contract plus bid-ask slippage, costs can consume 10-20% of theoretical gamma profits.
- **Too rare**: Miss profitable oscillations; delta drifts significantly, exposing you to directional risk.

**Practical approaches:**
1. **Time-based**: Rehedge at fixed intervals (every hour, every day)
2. **Delta-threshold**: Rehedge when delta exceeds a band (e.g., +/- 0.10)
3. **Volatility-adjusted**: Widen bands in low vol, narrow in high vol
4. **Hybrid**: Combine threshold triggers + time-based checks + volatility adjustments

### 1.6 The Zakamouline Optimal Hedging Bandwidth

Zakamouline (2006) developed a rigorous framework for optimal hedging under transaction costs:

- **Core idea**: Rather than hedging to exact Black-Scholes delta, maintain a *bandwidth* around the theoretical delta. Only rehedge when the actual hedge ratio moves outside this band.
- **The bandwidth depends on**:
  - Transaction cost level (wider band for higher costs)
  - Absolute value of gamma (the "curvature" of the option's payoff)
  - Time to expiry (bands narrow near expiry as gamma increases)
  - Risk aversion parameter
- **Performance**: The utility-based hedging strategy exhibits the best risk-return tradeoff across all risk metrics. Hedging to a fixed bandwidth, though a rough simplification, outperforms all other conventional strategies (fixed-time, fixed-delta-move, etc.).
- **Building on Whalley-Wilmott (1997) and Barles-Soner (1998)**: The hedging bandwidth is proportional to the cube root of transaction costs and inversely related to risk aversion.

**Practical takeaway**: Do not hedge to exact delta. Instead, compute an optimal bandwidth around delta based on your transaction costs and gamma exposure, and only rehedge when the boundary is breached.

### 1.7 Discrete vs. Continuous Hedging

In theory (Black-Scholes), continuous hedging perfectly replicates the option. In practice:

- **Continuous hedging is impossible**: Markets close, executions take time, each trade has costs
- **Discrete hedging introduces "hedging error"**: The gap between continuous theory and discrete reality is itself a source of P&L variance
- **Discrete-time gamma-hedging** has a higher order rate of convergence than simple delta-hedging
- **The reality**: Finding the optimal balance between hedging frequency and transaction costs is the central challenge. Too much hedging = cost drag. Too little = uncontrolled delta exposure.

### 1.8 Gamma Scalping with 0DTE Options

The rise of 0DTE (zero days to expiration) options has created a new frontier:

- 0DTE options now represent **over 40% of total S&P 500 options volume**
- ATM 0DTE options have **extremely high gamma** -- small moves in the underlying cause large delta changes
- Dealers who are short 0DTE gamma must hedge continuously, creating feedback loops:
  - **Short gamma dealers**: Buy rallies, sell dips -- amplifying moves
  - **Long gamma dealers**: Sell rallies, buy dips -- dampening moves
- The "gamma explosion" near expiry creates intense pinning effects around strikes with concentrated open interest
- **For gamma scalpers**: 0DTE offers the highest gamma-per-dollar but also the fastest theta decay. Realized vol must be very high to overcome the extreme time decay.
- ATM options lose 50-70% of their value in the final 3 days of life

---

## 2. VARIANCE TRADING

### 2.1 Variance Swaps

A variance swap is an OTC derivative whose payoff at expiry equals:

```
Payoff = Notional * (sigma_realized^2 - K_variance^2)
```

Where:
- **sigma_realized^2**: annualized realized variance over the swap's life
- **K_variance**: the strike (fair variance level agreed at inception)
- **Notional**: the vega notional (exposure per point of variance)

The buyer of a variance swap profits when realized variance exceeds the strike; the seller profits when markets are calmer than priced.

### 2.2 Realized Variance Calculation

```
RV = (252 / N) * SUM[ ln(S_i / S_{i-1})^2 ]   for i = 1 to N
```

Where:
- 252 = annualization factor (trading days per year)
- N = number of observed returns
- ln(S_i / S_{i-1}) = daily log return
- **No mean subtraction** (market convention for variance swaps)
- Realized volatility = sqrt(RV)

### 2.3 Static Replication with Options

A variance swap can be replicated using a static portfolio of options. This is the foundation of the modern VIX calculation.

**The key insight** (Demeterfi, Derman, Kamal, Zou, 1999): A short log contract is equivalent to holding a portfolio of OTM puts and calls, each weighted by **1/K^2** (inverse strike squared).

```
Variance Swap = (2/T) * [ integral from 0 to F of (1/K^2) * P(K) dK
                         + integral from F to infinity of (1/K^2) * C(K) dK ]
```

Where:
- P(K) = OTM put price at strike K
- C(K) = OTM call price at strike K
- F = forward price
- T = time to expiry

**Practical replication:**
- Use all available OTM puts (below forward) and OTM calls (above forward)
- Weight each by 1/K^2 * deltaK (where deltaK = strike spacing)
- The 1/K^2 weighting gives more weight to low strikes (crash risk)
- This is essentially the VIX formula (CBOE switched to this in 2003)

### 2.4 Trading the Variance Risk Premium (VRP)

The VRP is the persistent difference between implied variance and subsequently realized variance:

```
VRP = IV^2 - E[RV^2]
```

**Historical evidence:**
- From 1990-2018, average VIX (implied) was 19.3% while average realized volatility was 15.1% -- a 4.2% gap (CBOE/Bondarenko 2019)
- Selling variance swaps produced Sharpe ratios 4-5x higher than the equity market over a 20-year period
- The VRP is **pervasively negative** across stock indices, individual stocks, and ETFs
- It predicts equity returns, explaining up to 20% of variation in future monthly returns

**How to trade it:**
- **Sell variance swaps** (OTC, for institutions)
- **Sell straddles/strangles** (listed options, delta-hedged)
- **Sell VIX futures** in contango
- **Short VIX ETPs** (SVXY, etc.)

**Risks:**
- Variance swaps have **unlimited downside** for the seller
- 2008: VIX spiked to 80+; variance swap sellers faced catastrophic losses
- 2020: VIX spiked to 82 intraday on March 16
- Feb 2018 "Volmageddon": SVXY lost >80% in a single day
- The return distribution is extremely abnormal -- put sellers have historically incurred losses up to -800%

**Key finding**: The VRP during nontrading overnight periods is significantly negative (insurance-like), while during intraday trading it becomes positive or insignificant.

### 2.5 Variance Swap vs. Volatility Swap: The Convexity Adjustment

**The mathematical relationship:**

By Jensen's inequality (since sqrt is concave):

```
E[sqrt(V)] <= sqrt(E[V])
```

Therefore:
```
K_vol <= sqrt(K_var)
```

The fair volatility strike is always less than or equal to the square root of the fair variance strike. The difference is the **convexity adjustment**.

**Approximation formula:**
```
K_vol ~ sqrt(K_var) - Var(V) / (8 * E[V]^(3/2))
```

**Why it matters:**
- Variance swap payoff is **convex** in volatility: gains accelerate as vol rises, losses decelerate as vol falls
- Volatility swap payoff is **linear** in volatility
- A long variance swap position benefits from the convexity: boosted gains, discounted losses
- Variance swaps are therefore worth MORE than volatility swaps (the convexity premium)
- The wider the distribution of future variance, the larger the convexity adjustment

---

## 3. DISPERSION TRADING

### 3.1 Concept

Dispersion trading exploits the relationship between index volatility and its components:

```
sigma_index^2 = SUM_i SUM_j [w_i * w_j * sigma_i * sigma_j * rho_ij]
```

Simplified:
```
Index vol ~ Weighted average component vol * Average correlation
```

**The trade:**
- **Sell index volatility** (sell SPX straddles/strangles or variance swaps)
- **Buy component volatility** (buy straddles/strangles on top SPX stocks)
- This is a **short correlation** trade

If realized correlation < implied correlation, the dispersion trade profits.

### 3.2 Why It Works: The Correlation Risk Premium

**Empirical evidence:**
- Average implied correlation for S&P 500: **39.5-46.7%**
- Average realized correlation: **28.9-32.5%**
- This gap (7-18 percentage points) represents a large negative correlation risk premium
- Implied correlation consistently overstates subsequent realized correlation

**Why does this premium exist?**
1. **Structural demand**: Structured product sellers (autocallables, etc.) create consistently higher demand for index options than single-stock options
2. **Hedging demand**: Portfolio managers buy index puts for portfolio protection, pushing up index IV
3. **Risk premium**: Investors demand compensation for correlation risk because correlations spike during crises (exactly when you least want them to)

### 3.3 Implementation

**Instruments:**
- Sell ATM SPX straddle (or strip of OTM options for variance swap replication)
- Buy ATM straddles on top 20 SPX components (weight by index weight)
- Delta-hedge the entire portfolio to maintain neutrality

**Sizing and matching -- three approaches:**

| Method | Definition | Properties |
|--------|-----------|------------|
| **Vega-weighted** | Match vega of index leg to sum of single-stock vegas | Zero net vega by definition. Short gamma, short theta. |
| **Gamma-weighted** | Match gamma (vega/vol) on both legs | Since single-stock vol > index vol, the single-stock vega leg is larger. |
| **Theta-weighted** | Match vega * sqrt(variance) on both legs | Smallest single-stock leg of the three methods. |

**Critical practical considerations:**
- A vega-neutral book is NOT truly correlation-neutral during stress -- correlation shocks hit through gamma, not vega
- Real-world costs: 300 bps basket crossing + 15-50 bps carry/funding + mismatch/gamma noise can fully offset theoretical edge
- Delta must be adjusted frequently (some desks adjust every 15 minutes when delta exceeds +/- 1)

### 3.4 Historical Performance and Risks

**Returns:**
- Academic studies report statistically significant returns of **14.5-26.5% per annum** after transaction costs
- Sharpe ratios of **0.34-0.40**
- Generally positive carry in normal markets

**Risks:**
- During crises, correlations spike toward 1.0 -- the dispersion trade loses catastrophically
- 2008, 2020, Aug 2024: all saw correlation spikes
- Fat-tail risk: the strategy has positive expected carry but is exposed to extreme left-tail losses
- The trade is effectively short a correlation call -- unlimited loss potential on correlation spikes

---

## 4. VOLATILITY ARBITRAGE

### 4.1 The Core Signal

Volatility arbitrage seeks to exploit mispricings between implied volatility and expected realized volatility:

```
If E[RV] > IV  -->  Buy vol (buy straddles, buy variance swaps)
If E[RV] < IV  -->  Sell vol (sell straddles, sell variance swaps)
```

The "edge" comes from having a superior forecast of future realized volatility compared to what the options market implies.

### 4.2 Forecasting Models

**GARCH (Generalized Autoregressive Conditional Heteroskedasticity):**
- Models time-varying volatility with mean reversion
- Captures volatility clustering (high vol begets high vol)
- Widely used; covered extensively in Sinclair's framework
- Limitations: assumes symmetric response to returns (standard GARCH)

**HAR-RV (Heterogeneous Autoregressive Realized Volatility) -- Corsi (2009):**
- The "workhorse" model for realized volatility forecasting
- Based on the Heterogeneous Market Hypothesis: traders at different time horizons create different volatility components
- **Model structure -- HAR-RV(1,5,22):**

```
RV_{t+1} = c + beta_D * RV_t + beta_W * RV_t^(w) + beta_M * RV_t^(m) + epsilon
```

Where:
- RV_t = daily realized volatility
- RV_t^(w) = average RV over past 5 days (weekly)
- RV_t^(m) = average RV over past 22 days (monthly)

- Parsimoniously captures long memory in volatility
- Consistently outperforms GARCH for multi-day horizons
- Extensions: HAR-CJ (jump-adjusted), HAR-RS (regime-switching)

**Realized Kernels:**
- Non-parametric estimators of daily variance using intraday data
- Handle market microstructure noise (bid-ask bounce, etc.)
- More accurate than simple sum-of-squared-returns at high frequencies

### 4.3 P&L Attribution: Vega, Gamma, and Theta

The P&L of a delta-hedged option position decomposes into:

```
Total P&L = Delta P&L + Gamma P&L + Theta P&L + Vega P&L + Vanna P&L + Volga P&L + ...
```

For a delta-hedged position:

| Component | Source | Formula (approximate) |
|-----------|--------|----------------------|
| **Gamma P&L** | Realized price moves vs. hedging | (1/2) * Gamma * dS^2 |
| **Theta P&L** | Time decay | Theta * dt (negative for long options) |
| **Vega P&L** | Changes in implied vol | Vega * d(sigma_implied) |
| **Vanna P&L** | Cross-effect of spot and vol moves | Vanna * dS * d(sigma) |
| **Volga P&L** | Vol-of-vol effect | (1/2) * Volga * d(sigma)^2 |

**Key relationships:**
- If held to expiry and hedged frequently: P&L converges to **Gamma P&L + Theta P&L** (vega P&L washes out)
- When RV > IV: Gamma P&L > |Theta P&L| --> profit
- When RV < IV: Gamma P&L < |Theta P&L| --> loss
- Mark-to-market P&L includes vega P&L from IV changes (relevant for shorter holding periods)

### 4.4 Euan Sinclair's Framework for Vol Trading Edge

Sinclair's approach (from *Volatility Trading* and *Positional Option Trading*):

**Edge Decomposition:**
```
Expected Profit = Forecast Accuracy * Position Sizing * Execution Quality
```

1. **Forecast accuracy**: The ability to predict realized vol better than the market implies. Even a small edge (1-2 vol points) can be highly profitable if applied consistently.

2. **Position sizing (Kelly Criterion)**:
   - Sinclair's treatment uniquely incorporates estimation uncertainty, skewness of returns, and stop losses
   - f* = (p * b - q) / b (basic Kelly)
   - In practice, use fractional Kelly (e.g., half-Kelly) to account for parameter uncertainty
   - Key insight: the utility of directional options strategies depends on your ability to predict returns, "which probably isn't very good"

3. **Execution quality**: Minimizing slippage, optimal hedge ratios, timing of entry/exit

**Sinclair's core principles:**
- Develop a consistent process: have a goal, find trades with a clear statistical edge, and capture that edge
- The vol forecast matters more than the trade structure
- Position sizing is as important as the forecast itself
- Accept that you will be wrong often; ensure the expectancy is positive over many trades

---

## 5. TERM STRUCTURE TRADING

### 5.1 Calendar Spreads (Options)

**Structure:**
- Sell near-term option (e.g., 30 DTE)
- Buy far-term option (e.g., 60 DTE)
- Same strike price (pure calendar) or different (diagonal)

**Profit when:**
- Term structure steepens (near-term IV drops faster than far-term)
- Near-term option decays faster (theta advantage)
- Underlying stays near the strike

**Risk when:**
- Term structure inverts or flattens further
- Large underlying moves (gamma of near-term exceeds far-term)
- Near-term IV spikes (event risk)

**Optimal structure:**
- Sell ~30 DTE, buy ~60 DTE for the best balance of theta capture vs. gamma risk
- ATM strikes maximize theta differential
- Avoid holding through events that could cause near-term IV spikes

### 5.2 VIX Futures Term Structure Trading

The VIX term structure describes the relationship between VIX futures at different expirations:
- **Contango**: Longer-dated futures > shorter-dated futures (normal state ~84% of the time)
- **Backwardation**: Shorter-dated > longer-dated (signals fear/crisis)

**Roll yield mechanics:**
- In contango, VIX futures naturally decay toward spot VIX as expiration approaches
- Short VIX futures systematically earn this "roll yield"
- Average daily contango: ~5.6% (median 6.3%)

**Systematic contango harvesting strategy:**
- Sell the nearest VIX future with at least 10 trading days to maturity when in contango
- Buy VIX futures when the basis is in backwardation
- Hedge market exposure with E-mini S&P 500 futures
- Daily roll threshold: contango > 0.10 points / backwardation < -0.10 points
- Hold for approximately 5 trading days

### 5.3 VIX ETPs as Vehicles

| Product | Exposure | Key Characteristics |
|---------|----------|-------------------|
| **VXX** | Long VIX futures (M1/M2 blend) | Loses ~40-80% annually in contango. Down 98%+ since inception. |
| **UVXY** | 1.5x Long VIX futures | Even faster decay: 70-90% annual loss in contango |
| **SVXY** | -0.5x Short VIX futures | Profits from contango roll yield. Lost >80% during Feb 2018 Volmageddon. |

**Critical risk**: VIX spikes can destroy months or years of accumulated carry in a single session. The February 2018 event demonstrated that even -1x short VIX exposure can be catastrophic.

### 5.4 Diagonal Spreads: Directional + Term Structure

**Structure:**
- Buy longer-dated option at one strike
- Sell shorter-dated option at a different strike

**This combines:**
- A directional view (bullish if call diagonal, bearish if put diagonal)
- A term structure view (benefit from near-term theta decay)
- A volatility view (near-term IV richer than far-term)

### 5.5 Poor Man's Covered Call (PMCC)

**Structure:**
- Buy deep ITM LEAP call (high delta, ~0.70-0.85, 6-24 months out)
- Sell near-term OTM call (30-45 DTE)

**Mechanics:**
- The LEAP acts as a stock substitute (high delta) at 15-35% of the cost of 100 shares
- Sell covered calls against it repeatedly, reducing cost basis
- Capital savings: typically 55-85% less capital than a traditional covered call

**Key considerations:**
- Maximum loss: net debit paid (both options expire worthless)
- Best when: stock finishes near short call strike at near-term expiry
- Use limit orders for LEAP entry (wide bid-ask spreads)
- Theta: benefits short call, hurts LEAP (net theta can be positive or negative depending on strikes)
- As short calls expire, the LEAP retains time value, allowing repeated income generation

---

## 6. SKEW TRADING

### 6.1 Understanding Volatility Skew

Volatility skew describes the pattern where OTM puts trade at higher implied volatility than ATM or OTM calls. This "put skew" is persistent in equity markets due to:
- Demand for downside hedging (portfolio insurance)
- Structural selling of upside calls (covered call writing)
- Crash risk perception (post-1987 phenomenon)

**Skew measurement:**
- Risk reversal: IV(25-delta put) - IV(25-delta call)
- Skew slope: change in IV per unit change in delta or moneyness

### 6.2 Risk Reversals

**Structure:**
- Sell OTM put + Buy OTM call (bullish risk reversal) -- or reverse
- Minimal vega/gamma/theta exposure; primarily a skew trade

**When to use:**
- When put skew is "too steep": sell overpriced OTM puts, buy relatively cheap OTM calls
- When put skew is "too flat": buy "cheap" OTM puts, sell relatively rich OTM calls
- The position reveals market positioning: strongly positive risk reversal signals worry about downside; strongly negative signals optimism

### 6.3 Ratio Put Spreads as Skew Trades

**Structure (example):**
- Sell 1 ATM put (e.g., 100 strike)
- Buy 2 OTM puts (e.g., 90 strike)

**P&L profile:**
- **Stock stays flat**: ATM put sold expires worthless or near-worthless; OTM puts expire worthless. Net: collect premium.
- **Stock crashes hard (below 80)**: 2 long OTM puts gain value faster than 1 short ATM put loses. Net: profit accelerates.
- **Moderate decline (between 90-100)**: Worst case. Short ATM put loses, long OTM puts are still OTM. Maximum loss occurs near the long put strike.

**Skew connection:**
- Net vega depends on skew: steeper skew means OTM puts are more expensive, reducing the credit received
- Profitable when: stock stays flat OR crashes hard
- Loses in: moderate decline (worst case between strikes)

### 6.4 Skew Mean Reversion

**Key observation**: For most equities, there is a "typical" skew shape. When skew deviates from this norm, trading opportunities arise if you expect mean reversion.

**Evidence:**
- Steep put skew tends to predict future flattening
- Skew steepness increases around events and during stress, then reverts
- Kalman filter models produce the best forecasts of skew dynamics (both upper and lower tail behavior)
- Surface dynamics (sudden changes in specific areas of the vol surface) often precede significant price movements

**Trading the mean reversion:**
- When skew is abnormally steep: sell OTM puts, buy ATM options
- When skew is abnormally flat: buy OTM puts (cheap protection)
- Monitor skew z-scores relative to historical norms

---

## 7. EARNINGS VOLATILITY STRATEGIES

### 7.1 Pre-Earnings IV Run-Up Strategy

**The phenomenon:**
- IV creeps up days or weeks before earnings, reflecting uncertainty
- High-beta/growth stocks have the most dramatic pre-earnings IV surges
- Some stocks show steady IV climb; others have sudden 5-10 point jumps in the last 24-48 hours
- Typical IV increase: 20-50% in the week before earnings

**Strategy: Buy premium early, sell before announcement**
1. Buy straddle/strangle 5-10 trading days before earnings
2. Ride the IV expansion as the event approaches
3. Sell the position 1-2 days before the actual announcement
4. Avoid the post-earnings vol crush entirely

**Advantages:**
- Does not require predicting earnings direction or magnitude
- Profits from the predictable IV expansion pattern
- Lower risk than holding through the actual event

### 7.2 Selling Earnings Premium (Vol Crush Strategy)

**The phenomenon:**
- IV peaks the day before earnings
- After the announcement, IV collapses ("vol crush") -- often losing 30-40%+ of IV in one session
- The rapid repricing of options generates profit for sellers

**Strategy:**
1. Sell straddle or strangle 1-2 days before earnings
2. Collect the elevated premium
3. After earnings: IV crushes, options lose value rapidly
4. Close the position for a profit (if the stock move was within the expected range)

**Risk:**
- Big moves exceeding the premium collected
- Unlimited risk for naked short straddles
- Defined risk alternative: iron condors

**Which stocks consistently overprice earnings vol?**
- Compare inter-earnings implied volatility to historical actual earnings moves
- Look for stocks where the "expected move" (straddle price) consistently exceeds the actual move
- The options market generally does a good job predicting magnitude, but there are significant outliers -- these outliers are the opportunity

### 7.3 Earnings Iron Condor

**Structure:**
- Sell narrow iron condor around the expected move
- Short put at expected-move-down, short call at expected-move-up
- Buy protective wings further out

**Optimization:**
- Wing width based on historical move distribution
- Tighter wings = higher credit but lower win rate
- Wider wings = lower credit but higher win rate
- Historical analysis shows the expected move is exceeded about 30-35% of the time for SPX constituents

### 7.4 Post-Earnings Announcement Drift (PEAD) with Options

**Academic finding:**
- After earnings surprises, stock prices continue drifting in the direction of the surprise for weeks to months
- Abnormal returns: 2.6-9.37% per quarter (5.1% risk-adjusted over 3 months in one study)
- Exploiting both EAR (Earnings Announcement Return) and SUE (Standardized Unexpected Earnings) generates ~12.5% annual abnormal returns

**Options approach:**
- After a positive earnings surprise + favorable post-announcement drift signal:
  - Buy call spreads or bull put spreads to capture continued drift
  - Use options for leveraged exposure with defined risk
- After a negative earnings surprise:
  - Buy put spreads or bear call spreads
  - Options limit downside while capturing drift

---

## 8. TAIL RISK STRATEGIES

### 8.1 Systematic Tail Hedging

**Core approach:**
- Buy OTM puts (5-10% OTM), 30-60 DTE, rolling monthly
- Cost: typically 0.5-2% of portfolio per year (some estimates range to 18-30% for aggressive hedging)
- Protection: 3-10x payoff in crashes

### 8.2 Tail Hedge Optimization

**Strike selection:**
- Research examines 15 combinations: 30, 45, 60, 90, and 120 DTE x 0.03, 0.05, and 0.10 delta
- Lower delta (further OTM) = cheaper but requires larger crash to pay off
- Higher delta (closer to ATM) = more expensive but activates on smaller declines
- Some managers (e.g., 36 South) prefer very far OTM strikes with weighted average expiry of 3-6 years

**DTE selection:**
- Weekly: cheapest per unit, but rolls frequently (high transaction costs)
- Monthly (30-60 DTE): most common; balances cost vs. frequency
- Quarterly: lower roll frequency, but gap risk between rolls
- Long-dated (1-3+ years): lowest annualized carry cost, but significant capital tied up

**Portfolio allocation:**
- Taleb's recommendation: spend 1-3% of portfolio annually on tail protection
- The most valuable component may not be direct crash payoff but the ability to profit from the market's re-pricing of risk (IV spike -> roll puts before expiry at profit)

### 8.3 VIX-Based Hedging

**VIX calls as crash protection:**

| Factor | VIX Calls | SPX Puts |
|--------|-----------|----------|
| **Exposure** | Pure vol exposure | Direct price exposure |
| **Basis risk** | Yes -- VIX only moves inversely to SPX ~88% of the time | Minimal |
| **Liquidity in stress** | Can dry up | Generally maintained |
| **Payoff profile** | Explosive but short-lived | Steady, proportional to decline |
| **Roll cost** | High (contango) | Moderate |
| **Best for** | Sudden VIX spikes (flash crashes) | Orderly corrections |

**Typical cost:** 0.5-2% per month for continuous VIX call hedging programs.

**Key limitation:** VIX spikes are often short-lived. If options expire before or after the vol event, the hedge is ineffective. Swift action is required to monetize gains.

### 8.4 Put Spread Collars

**Structure (three-legged):**
1. **Buy protective put** (e.g., 95% of spot)
2. **Sell covered call** (e.g., 110% of spot) -- finances the put
3. **Sell further OTM put** (e.g., 85% of spot) -- further reduces cost

**Result:**
- Near-zero cost (credits from short call + short put offset long put cost)
- Protection between 85% and 95% of current price
- Capped upside above 110%
- Partial protection only (exposed below 85%)

**Put spread collar advantages over regular collar:**
- The long put can be purchased much closer to the money
- Greater upside potential vs. traditional collar
- Trade-off: exposed to catastrophic decline below the short put strike

---

## 9. REGIME-BASED VOLATILITY STRATEGIES

### 9.1 Identifying Volatility Regimes

| Regime | VIX Level | Characteristics | Optimal Strategy |
|--------|-----------|----------------|-----------------|
| **Low vol** | < 15 | Complacency; compressed premiums | Sell premium (small size); gamma scalp rarely; buy tail hedges (cheap) |
| **Normal vol** | 15-25 | Balanced market; normal uncertainty | Balanced approach; sell premium selectively; moderate hedging |
| **High vol** | 25-40 | Elevated fear; wide bid-asks | Sell premium carefully with tighter stops; reduce position sizes; increase hedge ratios |
| **Crisis vol** | > 40 | Panic; dislocations; illiquidity | Only buy premium; wait for opportunity; deploy tail hedges; avoid selling into panic |

### 9.2 Regime-Switching Models

**Hamilton (1989) Markov Regime-Switching:**
- Models the economy/market as existing in one of several discrete states
- Transitions between states follow a Markov chain (probability of switching depends only on current state)
- Extended by Hamilton and Susmel (1994) with SWARCH: regime-switching in the volatility level itself

**Hidden Markov Models (HMMs) for volatility:**
- Identify 2+ states of market behavior (e.g., "calm" and "turbulent")
- The volatility premium undergoes temporal breaks in its behavior
- Trading strategy: sell volatility in the "calm" regime; switch to Treasury Bills when the HMM signals transition to "turbulent"
- Regime-switching models provide better in-sample fit and out-of-sample forecasting than constant-parameter models

**Key academic findings:**
- Including VIX as a forward-looking feature enhances model responsiveness to shifts in market sentiment
- Volatility dynamics exhibit regime-dependent statistical properties
- Abrupt transition (Markov-switching) is preferred to smooth transition approaches for capturing vol regime changes

### 9.3 VIX Mean Reversion

**The iron law of VIX**: VIX always reverts to its long-term mean (~18-20), but timing matters enormously.

- VIX is bounded below (cannot go negative) and effectively bounded above (historical max ~82)
- After spikes, VIX typically mean-reverts within 30-90 days
- Half-life of VIX shocks: approximately 30-45 days
- BUT: mean reversion is not guaranteed on any specific timeline

### 9.4 GEX Regime Overlay with VIX Regime

**Gamma Exposure (GEX) adds a structural layer to VIX regime analysis:**

- **Positive GEX (dealers long gamma):** Dealers sell rallies, buy dips --> dampens volatility, creates range-bound action. This environment is favorable for premium selling.
- **Negative GEX (dealers short gamma):** Dealers buy rallies, sell dips --> amplifies moves, increases realized vol. This environment favors gamma scalping (long gamma).

**Combining VIX + GEX:**

| VIX Regime | GEX Regime | Interpretation | Strategy |
|-----------|------------|---------------|----------|
| Low VIX | Positive GEX | Maximum compression; calm | Sell premium; cheap tail hedges |
| Low VIX | Negative GEX | Calm but unstable; breakout risk | Buy gamma; prepare for move |
| High VIX | Positive GEX | Fear but dealers stabilizing | Sell premium into elevated IV |
| High VIX | Negative GEX | Maximum instability; crisis | Do not sell premium; buy wings |

---

## 10. POSITION MANAGEMENT AND ADJUSTMENT

### 10.1 When to Adjust vs. When to Close

**Close the position when:**
- The trade thesis is invalidated
- Maximum acceptable loss is reached
- Better opportunities exist elsewhere
- The risk/reward has deteriorated beyond acceptable levels

**Adjust the position when:**
- The trade thesis is still valid but the position needs rebalancing
- One side of a multi-leg strategy is under pressure
- Greeks have drifted from target levels
- You can improve the position's risk/reward without fundamentally changing the thesis

### 10.2 Rolling Mechanics

**Roll out in time (same strike, later expiration):**
- Close near-term position, open same strike in later expiration
- Adds time for the trade to work
- Usually done for a debit (costs money)
- Best when: underlying is near the strike but time is running out

**Roll out and down/up (new strike + later expiration):**
- Close near-term position, open new position at different strike in later expiration
- Resets the trade at a more favorable strike
- Can sometimes be done for a credit (if rolling in the direction of the underlying's move)
- Best when: the underlying has moved against you but you believe in mean reversion

**Cost analysis:**
- Always calculate the net debit or credit of the roll
- Compare the rolled position to simply closing and opening a fresh trade
- A roll that costs too much debit may be worse than taking the loss

### 10.3 Iron Condor Adjustment Rules

**The adjustment trigger:**
- Adjust when the underlying reaches the short strike or when the short strike delta touches ~25
- A practical rule: adjust when the stock gets within 3% of the short strike
- Some practitioners use a "1/3 width" rule: adjust when tested at 1/3 of the spread width

**Defensive tactics:**

1. **Roll the untested side closer** (collect additional credit):
   - If the put spread is under pressure, roll the call spread down to collect more credit
   - This tightens the condor but reduces risk by adding to total credit

2. **Roll the tested side away** (give more room):
   - Roll the challenged spread further OTM to a later expiration
   - Costs a debit but buys time and distance

3. **Leave the tested side alone**:
   - Counterintuitive but often correct: don't chase a losing side
   - Instead, adjust the untested side for additional credit

4. **Time-based roll**:
   - If the condor reaches 14 DTE and is not profitable, roll the entire condor to a later expiration
   - Resets theta decay and gives the position more time

### 10.4 Dynamic Delta Hedging

**How often to rebalance:**
- Combine threshold triggers with time-based checks and volatility adjustments
- In high-vol environments: tighter thresholds, more frequent rebalancing
- In low-vol environments: wider thresholds, less frequent rebalancing
- Near expiry: gamma increases dramatically -- may need minute-by-minute monitoring for short-dated positions

**Key considerations:**
- As expiration approaches, gamma sensitivity increases exponentially
- Rolling strategies can reduce gamma exposure near expiry
- Transaction costs must be factored into every rebalance decision

### 10.5 Portfolio-Level Greeks Optimization

**Net portfolio Greeks management:**
- Monitor aggregate delta, gamma, theta, vega across all positions
- Target ranges for each Greek based on market regime and outlook
- Rebalance individual positions to maintain portfolio-level targets

**Example targets by regime:**

| Greek | Low Vol Regime | High Vol Regime | Crisis |
|-------|---------------|----------------|--------|
| **Delta** | Near zero | Near zero | Slight negative |
| **Gamma** | Slight negative (sell premium) | Neutral to slight positive | Positive (long wings) |
| **Theta** | Positive (collecting premium) | Moderate positive | Negative OK (paying for protection) |
| **Vega** | Slight negative | Neutral | Positive (long vol) |

---

## Key References and Sources

### Books
- **Euan Sinclair** - *Volatility Trading* (2nd Edition, Wiley) and *Positional Option Trading* (Wiley)
- **Sheldon Natenberg** - *Option Volatility & Pricing* (2nd Edition, McGraw-Hill)
- **Colin Bennett** - *Trading Volatility: Correlation, Term Structure and Skew*

### Academic Papers and Research
- **Corsi (2009)** - "A Simple Approximate Long-Memory Model of Realized Volatility" (HAR-RV model)
- **Hamilton (1989)** - Markov Regime-Switching model
- **Demeterfi, Derman, Kamal, Zou (1999)** - Variance swap replication (Goldman Sachs)
- **Carr and Lee** - "Realized Volatility and Variance: Options via Swaps"
- **Zakamouline (2006)** - Optimal hedging with transaction costs
- **Whalley and Wilmott (1997)** - Asymptotic analysis of utility-based hedging
- **Bondarenko (2019)** - "Historical Performance of Put-Writing Strategies" (CBOE)
- **Carr (2009)** - "Variance Risk Premia" (NYU/Bloomberg)

### Industry Research
- **CBOE** - VIX methodology, PUT/BXM index research, implied correlation indices
- **Quantpedia** - Dispersion trading, VRP, term structure strategies
- **TastyTrade/tastylive** - Premium selling studies, expected move analysis, 45 DTE optimization

---

*Document compiled February 2026. Strategies involve significant risk. Past performance does not guarantee future results. Options trading involves risk of substantial loss.*
