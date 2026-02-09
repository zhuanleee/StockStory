# Optimal Position Sizing, Kelly Criterion, and Portfolio Risk Management

## A Comprehensive Mathematical Treatment for Options Trading

---

## Table of Contents

1. [The Kelly Criterion -- Deep Mathematical Treatment](#1-the-kelly-criterion--deep-mathematical-treatment)
2. [Kelly Applied to Options Trading](#2-kelly-applied-to-options-trading)
3. [Fractional Kelly and Practical Sizing](#3-fractional-kelly-and-practical-sizing)
4. [Drawdown Management](#4-drawdown-management)
5. [Portfolio-Level Risk Management for Options](#5-portfolio-level-risk-management-for-options)
6. [The Sharpe Ratio and Its Limitations for Options](#6-the-sharpe-ratio-and-its-limitations-for-options)
7. [Monte Carlo Simulation for Options Portfolios](#7-monte-carlo-simulation-for-options-portfolios)
8. [Systematic Strategy Evaluation](#8-systematic-strategy-evaluation)
9. [Risk Management Rules -- What Works](#9-risk-management-rules--what-works)
10. [Behavioral Risk Management](#10-behavioral-risk-management)

---

## 1. The Kelly Criterion -- Deep Mathematical Treatment

### 1.1 Historical Foundation

John L. Kelly Jr. published "A New Interpretation of Information Rate" in 1956 while working at Bell Labs under Claude Shannon. Kelly's insight was that the problem of optimal gambling is mathematically identical to the problem of optimal data transmission over a noisy channel. Shannon himself brought Kelly's paper to Edward O. Thorp's attention in November 1960, and Thorp subsequently applied it to blackjack (Beat the Dealer, 1962) and later to warrant pricing and portfolio management (Beat the Market, 1967, with Sheen Kassouf).

Thorp went on to use Kelly-based portfolio optimization at Princeton-Newport Partners, generating 20% annualized returns over 28 years, wagering over $80 billion with an average of 100 simultaneous positions.

**Key academic lineage**: Kelly (1956) -> Breiman (1961, rigorizing Kelly's results) -> Thorp (1962, 1967, practical application) -> Merton (1969, 1971, continuous-time formulation) -> Cover & Thomas (1991, information-theoretic treatment in Elements of Information Theory).

### 1.2 The Original Kelly Formula: Binary Bets

**Setup**: A gambler faces repeated binary bets. Each bet of one unit returns (1 + b) with probability p (a win) or loses the wagered amount with probability q = 1 - p (a loss). The gambler bets a fraction f of their current bankroll on each trial.

**The optimization problem**: Find the fraction f that maximizes the long-run geometric growth rate of wealth.

After n bets, with W wins and L = n - W losses, the wealth evolves as:

```
W_n = W_0 * (1 + b*f)^W * (1 - f)^L
```

The geometric growth rate per bet is:

```
G(f) = (1/n) * log(W_n / W_0) = (W/n) * log(1 + b*f) + (L/n) * log(1 - f)
```

By the Law of Large Numbers, as n -> infinity, W/n -> p and L/n -> q, so:

```
G(f) = p * log(1 + b*f) + q * log(1 - f)
```

This is the expected logarithmic growth rate, equivalently E[log(1 + f*X)] where X is the bet outcome.

**Maximization**: Take the derivative and set to zero:

```
dG/df = p*b / (1 + b*f) - q / (1 - f) = 0
```

Solving:

```
p*b*(1 - f) = q*(1 + b*f)
p*b - p*b*f = q + q*b*f
p*b - q = f*(p*b + q*b) = f*b*(p + q) = f*b
```

Therefore:

```
f* = (b*p - q) / b
```

Or equivalently:

```
f* = p - q/b = p - (1-p)/b
```

**Verification**: The second derivative is:

```
d^2G/df^2 = -p*b^2 / (1 + b*f)^2 - q / (1 - f)^2 < 0
```

This is strictly negative for all f in (0, 1), confirming f* is a maximum (G is concave in f).

**Maximal growth rate**: Substituting f* back:

```
G(f*) = p * log(p*(1+b)) + q * log(q*(1+b)/b)
       = p * log(p) + q * log(q) + log(1+b) + q * log(1/b)
```

### 1.3 Connection to Shannon Entropy and Information Theory

Kelly's original paper demonstrated that the maximum exponential growth rate of a gambler's capital equals the rate of information transmission over a communication channel. Specifically:

**Doubling rate and mutual information**: Let X be the race outcome and Y be the side information available to the gambler. The maximum doubling rate (growth rate of wealth) is:

```
W* = max_b E[log(b(X)o(X))]
```

where b(X) is the bet allocation and o(X) are the odds. Kelly showed:

```
W* = W*(uniform) + I(X; Y)
```

where I(X; Y) is the mutual information between the race outcome and the side information. The value of "inside information" in gambling is precisely measured by mutual information -- the same quantity that governs channel capacity in Shannon's communication theory.

**Growth rate as negative entropy**: The Kelly growth rate can be expressed as:

```
G(f*) = H(prior odds) - H(true distribution) = D_KL(p || implied_p)
```

where D_KL is the Kullback-Leibler divergence between the true probability distribution and the implied probabilities from the odds. When the gambler has perfect information, the growth rate equals the Shannon entropy of the outcome distribution.

**Channel capacity connection**: Kelly proved that the maximum growth rate with side information Y about outcome X is:

```
G_max = log(m) + D(p||q) + I(X;Y)
```

where m is the number of outcomes, D(p||q) is the divergence between true and offered probabilities, and I(X;Y) is the mutual information from side information.

This provides a profound insight: **the growth rate of wealth in repeated gambling is fundamentally an information-theoretic quantity**. The gambler's edge is measured in bits, and the rate of wealth accumulation is bounded by the channel capacity of the "information channel" between the gambler's knowledge and the market's prices.

### 1.4 Kelly for Continuous Outcomes (Gaussian Returns)

When returns are continuously distributed rather than binary, the Kelly framework generalizes naturally.

**Setup**: An asset has returns R ~ N(mu, sigma^2) per period, and there exists a risk-free asset earning rate r. The investor allocates fraction f to the risky asset.

Portfolio return per period:

```
R_p = r + f*(R - r)
```

The expected log growth rate is:

```
G(f) = E[log(1 + R_p)]
     ≈ E[R_p] - (1/2)*Var(R_p)        (second-order Taylor expansion for small returns)
     = r + f*(mu - r) - (1/2)*f^2*sigma^2
```

Maximize by taking derivative:

```
dG/df = (mu - r) - f*sigma^2 = 0
```

Solving:

```
f* = (mu - r) / sigma^2
```

**This is the Merton optimal portfolio fraction** for an investor with logarithmic utility. Merton (1969, 1971) derived this result independently in his continuous-time portfolio selection under uncertainty framework, confirming the deep connection between Kelly gambling and continuous finance.

Note: f* = (mu - r) / sigma^2 can also be written as f* = SR / sigma, where SR = (mu - r)/sigma is the Sharpe ratio. This means:

```
f* = Sharpe_Ratio / sigma = Sharpe_Ratio^2 / (mu - r)
```

The optimal Kelly fraction is directly proportional to the Sharpe ratio and inversely proportional to volatility. An asset with SR = 0.5 and sigma = 20% yields f* = 0.5/0.20 = 250% (i.e., 2.5x leverage), illustrating why full Kelly is often too aggressive.

### 1.5 Multi-Asset Kelly (Portfolio Kelly Criterion)

**Setup**: N risky assets with mean excess return vector (mu - r*1) and covariance matrix Sigma. The investor allocates fraction f_i to each asset i.

The expected log growth rate generalizes to:

```
G(f) = r + f^T*(mu - r*1) - (1/2)*f^T * Sigma * f
```

Maximizing:

```
dG/df = (mu - r*1) - Sigma * f = 0
```

Solving:

```
f* = Sigma^{-1} * (mu - r*1)
```

**This is the Markowitz tangent portfolio for log utility**. The Kelly criterion for multiple correlated assets yields the same allocation as mean-variance optimization with a logarithmic utility function. Thorp (1975) first established this equivalence explicitly.

**Key properties of the multi-asset Kelly solution**:

1. **Correlation matters**: Correlated assets receive smaller combined allocations. The covariance matrix Sigma accounts for all pairwise correlations.

2. **Uncorrelated special case**: When assets are uncorrelated (Sigma is diagonal), f*_i = (mu_i - r) / sigma_i^2 for each asset independently -- the single-asset Kelly applied separately.

3. **Extreme sensitivity to inputs**: The portfolio Kelly solution is approximately 20x more sensitive to errors in expected returns than to errors in the covariance matrix. This is the primary reason full Kelly is impractical.

4. **Leverage**: The sum of f*_i need not equal 1. The optimal Kelly portfolio can be levered (sum > 1) or hold cash (sum < 1).

### 1.6 Properties of the Growth Rate Curve

The growth rate G(f) as a function of the betting fraction f has critical properties:

**For the binary case**:

```
G(f) = p * log(1 + b*f) + q * log(1 - f)
```

- G(0) = 0 (no bet, no growth)
- G(f*) > 0 at the optimum (positive growth when there is an edge: bp > q)
- G is concave in f (second derivative strictly negative)
- There exists f_c > f* where G(f_c) = 0 (growth rate returns to zero)

**For the continuous case (Gaussian approximation)**:

```
G(f) = r + f*(mu - r) - (1/2)*f^2*sigma^2
```

This is a downward-opening parabola. The growth rate becomes zero when:

```
f*(mu - r) - (1/2)*f^2*sigma^2 = 0
f * [(mu - r) - (1/2)*f*sigma^2] = 0
```

Non-trivial zero at f = 2*(mu - r)/sigma^2 = **2*f_Kelly**

**Critical result**: At exactly twice the Kelly bet (f = 2f*), the growth rate equals the risk-free rate. Beyond 2f*, the growth rate is negative -- the gambler is guaranteed to lose money in the long run, even with a positive edge.

This parabolic property gives Kelly its "point of no return":

| Fraction of Kelly | Growth Rate (% of maximum) |
|---|---|
| 0.25 * f* | ~44% |
| 0.50 * f* | ~75% |
| 0.75 * f* | ~94% |
| 1.00 * f* | 100% (maximum) |
| 1.50 * f* | ~75% |
| 2.00 * f* | 0% (zero excess growth) |
| 3.00 * f* | Negative (losing money) |

The symmetry around f* is exact for the Gaussian case: Half-Kelly (f*/2) and 1.5x Kelly produce the same growth rate (75% of maximum), but half-Kelly does so with far less risk.

---

## 2. Kelly Applied to Options Trading

### 2.1 Why Standard Kelly Does Not Directly Apply to Options

Options present several complications that break the assumptions of the standard Kelly framework:

1. **Non-binary outcomes**: Options do not simply "win" or "lose." A credit spread can be fully profitable, fully losing, or anywhere in between depending on where the underlying finishes relative to the strikes.

2. **Time-varying edge**: The expected value of an option position changes continuously due to theta decay, delta drift, and changes in implied volatility. The "edge" at entry may differ substantially from the edge at any subsequent point.

3. **Skewed and fat-tailed payoff distributions**: Long options have unlimited upside with limited downside (positive skew), while short options have limited upside and potentially catastrophic downside (negative skew). Neither matches the Gaussian assumption.

4. **Path dependency**: Many options strategies have outcomes that depend not just on the terminal price but on the path taken (e.g., early assignment risk, knock-out barriers, stop-loss triggers).

5. **Leverage is embedded**: Options are inherently leveraged instruments. A position "costing" $100 in premium may have risk exposure equivalent to thousands of dollars in stock.

### 2.2 Adapting Kelly for Credit Spreads (Defined Risk)

Credit spreads (e.g., bull put spreads, bear call spreads) have binary-like payoffs that make Kelly adaptation more tractable:

**Variables**:
- Credit received: C
- Width of spread: W
- Max loss: W - C
- Win probability: P_win (approximated by 1 - delta of short strike, or from implied probability)
- Loss probability: P_loss = 1 - P_win

**Kelly fraction for credit spreads**:

Treating this as a binary bet where the win amount is C and the loss amount is (W - C):

```
b = C / (W - C)     (odds ratio: profit per dollar of max risk)
p = P_win
q = P_loss = 1 - P_win

f* = (b*p - q) / b
   = p - q/b
   = p - q*(W - C) / C
   = [C*P_win - (W - C)*P_loss] / (W - C)
```

Equivalently, in terms of the original credit spread parameters:

```
f* = [C * P_win - (W - C) * P_loss] / (W - C)
```

Where f* represents the fraction of the bankroll to risk (i.e., the max loss of the position should equal f* times the total account value).

**Worked example**: Sell a $5-wide put spread for $1.50 credit, with 70% estimated win rate.

```
C = 1.50, W = 5.00, Max loss = 3.50
P_win = 0.70, P_loss = 0.30
b = 1.50 / 3.50 = 0.4286

f* = (0.4286 * 0.70 - 0.30) / 0.4286
   = (0.300 - 0.300) / 0.4286
   = 0 / 0.4286
   = 0
```

**Result: f* = 0**, meaning this trade has zero edge! The expected value is exactly zero:

```
EV = C * P_win - (W - C) * P_loss = 1.50 * 0.70 - 3.50 * 0.30 = 1.05 - 1.05 = 0
```

This is not a coincidence: when options are priced efficiently, the implied probability reflects fair pricing and the Kelly fraction is zero. **You need the actual win rate to exceed the implied win rate to have a positive Kelly fraction**.

**For a trade with actual edge**: Same spread, but you estimate true P_win = 80% (vs. 70% implied):

```
f* = [1.50 * 0.80 - 3.50 * 0.20] / 3.50
   = [1.20 - 0.70] / 3.50
   = 0.50 / 3.50
   = 0.143 (14.3% of bankroll)
```

At half-Kelly: f = 7.1% of bankroll, meaning max loss on this spread should not exceed 7.1% of total account.

### 2.3 Adapting Kelly for Long Options

Long options have fundamentally different characteristics:
- Lower win rate (typically 20-40% for OTM options)
- Much larger potential payoffs (5x-50x or more)
- The full distribution of outcomes matters, not just win/lose

**Approach**: Use the continuous Kelly for skewed distributions:

For a position with expected return mu and variance sigma^2 of the percentage P&L:

```
f* = mu / sigma^2
```

However, for highly skewed distributions (long options), this approximation is poor. Better approaches:

1. **Discretize outcomes**: Break the distribution into scenarios (big win, small win, breakeven, total loss) with probabilities, and numerically maximize E[log(1 + f*R)] over f.

2. **Monte Carlo Kelly**: Simulate thousands of possible outcomes using a stochastic volatility model, then find f that maximizes the average log return across simulations.

3. **Numerical optimization**: Use scipy.optimize or similar to maximize:

```
G(f) = (1/N) * sum_{i=1}^{N} log(1 + f * R_i)
```

over simulated returns R_1, ..., R_N.

### 2.4 Estimating Win Probabilities for Options

The core challenge: Kelly requires accurate probability estimates, which are inherently uncertain for options.

**Implied probabilities from option prices**: Delta is a rough proxy for the probability of an option expiring ITM. A 16-delta put has roughly a 16% chance of expiring ITM. However, delta incorporates risk premiums and is not a pure probability.

**Historical win rates by strategy type** (approximate ranges):
- ATM short straddle: 40-50% win rate, but defined at 50% of max profit
- 1-SD short strangle (16-delta): 68-72% win rate at expiration
- 30-delta short put spread: ~70% win rate
- 10-delta iron condor: ~80-85% win rate at expiration
- Closing at 50% profit: adds ~10-15% to win rate

**Bayesian updating**: Start with a prior (e.g., implied probability from delta) and update as you accumulate data. Use a Beta distribution as the conjugate prior for binomial win/loss outcomes:

```
Prior: P_win ~ Beta(alpha, beta)
After observing w wins and l losses:
Posterior: P_win ~ Beta(alpha + w, beta + l)
```

This systematically accounts for uncertainty in your edge estimates and naturally shrinks toward conservative estimates when data is limited.

---

## 3. Fractional Kelly and Practical Sizing

### 3.1 Why Full Kelly Is Too Aggressive

Full Kelly is optimal only under the assumption of **perfect knowledge of edge and probabilities**. In practice:

1. **Estimation error dominates**: Small errors in P_win or the payoff ratio drastically change f*. The Kelly solution is approximately 20x more sensitive to errors in expected returns than to errors in the covariance matrix.

2. **Severe drawdowns are expected**: Under full Kelly betting, even with known true probabilities:
   - Probability of a 50% drawdown at some point: ~50%
   - Probability of a 75% drawdown: meaningful
   - The expected time to recover from drawdowns is long
   - Full Kelly has a roughly 50% chance of experiencing a 50% drawdown during extended play

3. **Non-stationarity**: Markets change. An edge that existed last month may not exist this month. Full Kelly assumes a stationary edge.

4. **Psychological stress**: Full Kelly positions cause extreme P&L swings that are psychologically unsustainable for most traders.

5. **Estimation error destroys performance**: When probabilities are estimated rather than known, full Kelly systematically over-bets because over-estimation of edge leads to larger bets (which lose more) while under-estimation leads to smaller bets (which win less). This asymmetry means the average realized growth rate is substantially below the theoretical Kelly optimum.

### 3.2 Fractional Kelly Strategies

**Half-Kelly (f = f*/2)**:
- Achieves **75% of the optimal growth rate** (from the parabolic property of G(f))
- Approximately **50% less drawdown** than full Kelly
- The standard practitioner recommendation
- A 5-loss streak with 10% Kelly risk results in ~22.6% drawdown vs ~39% at full Kelly

**Quarter-Kelly (f = f*/4)**:
- Achieves ~44% of the optimal growth rate
- Very conservative; survives severe estimation errors
- Appropriate when:
  - Edge is uncertain or newly discovered
  - Sample size of historical trades is small (< 50)
  - Market regime is changing
  - Trading volatile or illiquid instruments (like options)

**Empirical Kelly fraction selection**:

| Confidence in Edge | Suggested Fraction | Rationale |
|---|---|---|
| Proven model, years of data | 50% Kelly (half) | Strong evidence, still conservative |
| Good model, moderate data | 33% Kelly (third) | Reasonable caution |
| Subjective judgment, limited data | 25% Kelly (quarter) | High uncertainty |
| New strategy, unproven | 10-20% Kelly | Essentially testing |

### 3.3 Anti-Kelly: The Dangers of Over-Betting

The most important insight from Kelly theory is not the optimal fraction itself, but what happens when you exceed it:

**At f = f***: Maximum growth rate G*
**At f = 1.5 * f***: Growth rate = 0.75 * G* (same as half-Kelly, but with MUCH more risk)
**At f = 2 * f***: Growth rate = 0 (zero excess growth -- all your edge is consumed by volatility drag)
**At f > 2 * f***: Growth rate is NEGATIVE -- you will go broke even with a winning strategy

The mathematical intuition is **volatility drag** (also called "variance drain"):

```
Geometric return ≈ Arithmetic return - (1/2) * Variance
```

A gain of X% followed by a loss of X% always produces a net loss:
- Lose 10%, gain 10%: end at 0.90 * 1.10 = 0.99 (down 1%)
- Lose 20%, gain 20%: end at 0.80 * 1.20 = 0.96 (down 4%)
- Lose 50%, gain 50%: end at 0.50 * 1.50 = 0.75 (down 25%)

The drag scales with the square of the volatility, which is why over-betting is catastrophic.

**Implication for options trading**: Because options are leveraged instruments, it is very easy to accidentally bet more than 2*f* without realizing it. A "2% position" in far-OTM options can have the risk characteristics of a 20%+ Kelly bet. Always think in terms of **max dollar risk relative to account**, not just the premium spent.

### 3.4 Ralph Vince's Optimal f

Ralph Vince extended Kelly's work to handle non-binary outcomes more rigorously. While Kelly uses average values from past trades, Vince's Optimal f takes into account all trades, optimizing the Terminal Wealth Relative (TWR) as a function of f:

```
TWR(f) = Product_{i=1}^{N} (1 + f * R_i / |R_worst|)
```

where R_i are historical returns and R_worst is the worst historical loss.

Optimal f solves: max_{f in [0,1]} TWR(f)

**Key differences from Kelly**:
- Optimal f is measured against the maximal historical loss, not as a simple fraction of bankroll
- It accounts for the full distribution of past returns, not just mean and variance
- The maximal drawdown with optimal f will be at least f_opt percent of the account
- Optimal f can suggest leverage greater than 1x since it is measured against worst-case loss

**In practice**: Optimal f should be treated as an upper bound. Most practitioners use it as a ceiling and actually trade at a fraction of it, analogous to fractional Kelly.

---

## 4. Drawdown Management

### 4.1 Drawdown Properties Under Kelly Betting

**Maximum drawdown scaling**: For a strategy with positive drift (positive edge):
- The expected maximum drawdown scales logarithmically with time: E[MDD] ~ O(log(T))
- For zero drift: E[MDD] ~ O(sqrt(T))
- For negative drift: E[MDD] ~ O(T) (linear -- the strategy is losing)

**Drawdown probability under Kelly**: The probability of experiencing a drawdown of depth d at some point during infinite play follows a power law:

```
P(drawdown > d) ≈ d^{-c}
```

where c depends on the edge (Sharpe ratio). For example, with full Kelly on a coin flip with 55% win probability, the probability of a 50% drawdown is approximately 1/2 (50%).

**Fractional Kelly and drawdown reduction**: Betting fraction alpha of Kelly reduces drawdown probability exponentially. The probability of reaching a drawdown level d:

```
P(drawdown > d | bet = alpha * f*) ≈ d^{-c/alpha}
```

So betting 30% of Kelly transforms a 1-in-5 chance of an 80% drawdown into a 1-in-213 chance -- a dramatic reduction in tail risk.

### 4.2 Risk of Ruin Calculations

**Simple case (binary bets)**: For a gambler with initial wealth W_0 betting fraction f per trial:

```
P(ruin) = ((1-f*) / f*)^{W_0 / unit_bet}   (for certain parameter regimes)
```

More practically, risk of ruin depends on:
- Win rate (p)
- Reward-to-risk ratio (R)
- Fraction risked per trade (f)
- Ruin threshold (typically 50% or 100% drawdown)

**Continuous approximation**: For a strategy with Sharpe ratio SR trading at leverage L:

```
P(permanent ruin) ≈ exp(-2 * SR * W_target / (L * sigma))
```

where W_target is the initial wealth level and sigma is portfolio volatility.

### 4.3 Risk-Constrained Kelly (Busseti, Ryu, Boyd, 2016)

Busseti et al. at Stanford developed a rigorous framework for Kelly betting with explicit drawdown constraints:

**Problem formulation**:
```
maximize    E[log(1 + f^T * R)]           (Kelly growth objective)
subject to  P(W_min < alpha) < beta        (drawdown risk constraint)
```

Where:
- alpha = maximum acceptable drawdown level (e.g., 0.80 means 20% drawdown)
- beta = maximum acceptable probability of that drawdown occurring

**Key result**: They develop a convex bound on the drawdown probability:

```
E[(r^T * b)^{-lambda}] <= 1
```

where lambda = log(beta) / log(alpha). This transforms the non-convex chance constraint into a convex optimization problem that can be solved efficiently.

**Practical result**: The risk-constrained Kelly fraction is parameterized by a single risk-aversion parameter lambda, which has a natural interpretation. Setting a 5% probability of a 20% drawdown (alpha = 0.80, beta = 0.05) typically yields a fraction between f*/3 and f*/5 -- consistent with the practitioner wisdom of quarter-Kelly to fifth-Kelly for uncertain strategies.

### 4.4 The Asymmetry of Drawdowns

The fundamental asymmetry of percentage losses:

| Drawdown | Required Recovery |
|---|---|
| 10% | 11.1% |
| 20% | 25.0% |
| 30% | 42.9% |
| 50% | 100.0% |
| 75% | 300.0% |
| 90% | 900.0% |

This non-linearity is the strongest argument for conservative position sizing. A 50% drawdown requires a 100% gain to recover -- which at a modest 15% annualized return takes approximately 5 years.

### 4.5 Ergodicity and Time Averages (Ole Peters)

Ole Peters and colleagues at the London Mathematical Laboratory have developed a framework called "ergodicity economics" that provides deeper theoretical justification for Kelly-like position sizing.

**Core insight**: In classical economics, expected utility theory maximizes the **ensemble average** (the average across many parallel gamblers at one point in time). But a single individual experiencing bets sequentially through time needs to maximize the **time average** (the average along a single trajectory through time).

For non-ergodic processes (which include multiplicative wealth dynamics), these two averages are NOT equal:

```
<X>_ensemble ≠ <X>_time
```

**Example**: A bet that gains 50% or loses 40% with equal probability.
- Ensemble average: E[R] = 0.5 * 1.50 + 0.5 * 0.60 = 1.05 (5% expected gain -- looks good!)
- Time average (geometric): (1.50 * 0.60)^{1/2} = 0.90^{1/2} = 0.949 (5.1% LOSS per period)

The ensemble average says "take this bet" while the time average says "this bet will ruin you." Kelly criterion naturally maximizes the time-average growth rate (which is the geometric growth rate), making it the correct framework for a single investor making sequential decisions.

**Implication**: Maximizing E[log(wealth)] is not just a utility preference -- it is the uniquely correct objective for an individual seeking to maximize long-term wealth growth. The logarithm arises from the multiplicative nature of wealth dynamics, not from diminishing marginal utility.

---

## 5. Portfolio-Level Risk Management for Options

### 5.1 Portfolio Greeks Management

The Greeks provide a real-time risk dashboard for an options portfolio:

**Net Delta** -- Directional exposure:
- Measures portfolio sensitivity to a $1 move in the underlying
- Target: near zero for market-neutral strategies, positive for bullish bias
- Systematic monitoring: maintain net portfolio Delta between -0.30 and +0.30 per unit of underlying for directional risk control
- Dollar delta: net delta times notional value -- the true measure of directional risk

**Net Gamma** -- Convexity exposure:
- Positive gamma: profits accelerate as the underlying moves (long options)
- Negative gamma: losses accelerate (short options -- the most dangerous Greek)
- Track total Gamma exposure: target between -0.20 and +0.20 to manage convexity risk
- Gamma risk is highest near expiration and near the short strikes

**Net Vega** -- Volatility exposure:
- Positive vega: benefits from rising implied volatility
- Negative vega: benefits from declining implied volatility
- Important because implied vol moves often dominate P&L for longer-dated options
- Should be balanced between long and short vol positions

**Net Theta** -- Time decay:
- Positive theta: earning income from time decay (premium sellers)
- The "daily rent" of an options portfolio
- Target: positive theta aligned with account size (e.g., 0.1-0.3% of account per day)
- Too much positive theta usually means too much negative gamma -- there is no free lunch

**The Theta-Gamma Trade-off**: There is a fundamental relationship:

```
Theta ≈ -(1/2) * Gamma * S^2 * sigma^2
```

Positive theta always comes with negative gamma (and vice versa). This means that premium sellers who collect theta are implicitly short gamma -- they profit from small moves but lose from large moves.

### 5.2 Risk Budgeting by Strategy

Rather than allocating capital equally, allocate **risk** by strategy type:

**Example risk budget**:
- Credit spreads (positive theta, negative gamma): 40% of risk budget
- Directional trades (long deltas or puts): 30% of risk budget
- Volatility plays (straddles, strangles): 20% of risk budget
- Event plays (earnings, catalysts): 10% of risk budget

**Measuring risk contribution**: Each position's contribution to portfolio risk is:

```
RC_i = f_i * (Sigma * f)_i / sqrt(f^T * Sigma * f)
```

where f_i is the allocation to position i and Sigma is the covariance matrix. The sum of all risk contributions equals the total portfolio volatility.

### 5.3 Correlation-Adjusted Position Sizing

**The problem**: Two 5% positions in AAPL and MSFT are not the same as two 5% positions in AAPL and XOM. Tech stocks are highly correlated, so the first portfolio has much more concentrated risk.

**Approaches**:

1. **Pairwise correlation adjustment**: If two positions have correlation rho, reduce each position size by a factor related to rho:

```
f_adjusted = f_individual / sqrt(1 + rho * (n-1))
```

where n is the number of correlated positions.

2. **Sector-based correlation heuristic**: A practical shortcut:
   - Same sector: assume rho = 0.6-0.8, size each position at 60-70% of standalone Kelly
   - Different sectors: assume rho = 0.3-0.5, size at 80-90% of standalone Kelly
   - Negatively correlated (e.g., long VIX + long SPY): can size larger as they hedge each other

3. **Principal Component Analysis (PCA)**: Decompose the portfolio's risk into principal components:
   - First PC typically represents market risk (explains 40-60% of variance)
   - Subsequent PCs capture sector, factor, and idiosyncratic risks
   - Size positions to ensure no single PC dominates portfolio risk
   - PCA transforms correlated assets into uncorrelated "principal portfolios," enabling cleaner risk allocation

### 5.4 Value at Risk (VaR) for Options Portfolios

VaR answers: "What is the maximum loss over a given time horizon at a given confidence level?"

**Parametric VaR (Delta-Normal)**:

```
VaR_alpha = -delta_portfolio * z_alpha * sigma * S * sqrt(T)
```

where z_alpha is the normal quantile (e.g., z_0.05 = 1.645). This ignores gamma and is adequate only for near-linear positions.

**Delta-Gamma VaR (Quadratic Approximation)**:

The portfolio P&L is approximated by a quadratic function:

```
Delta_P ≈ delta * Delta_S + (1/2) * Gamma * (Delta_S)^2
```

For the full portfolio with multiple risk factors:

```
Delta_P ≈ delta^T * Delta_S + (1/2) * Delta_S^T * Gamma_matrix * Delta_S
```

The distribution of this quadratic form is not normal even when Delta_S is normal, requiring numerical methods (Cornish-Fisher expansion, Monte Carlo, or Fourier methods) to compute VaR.

**Historical VaR**: Apply historical returns to the current portfolio:
1. Collect T historical return vectors
2. Recompute portfolio P&L for each historical scenario
3. VaR = negative of the alpha-th percentile of the resulting P&L distribution

**Monte Carlo VaR**: The gold standard for options portfolios:
1. Simulate N correlated price paths (using Cholesky decomposition for correlation)
2. Fully reprice all options under each scenario
3. VaR = negative of the alpha-th percentile of simulated portfolio values

**Why VaR understates tail risk for options**: VaR gives a single point on the loss distribution. For options with non-linear payoffs (especially short gamma positions), the distribution has a fat left tail. The average loss beyond VaR can be much larger than VaR itself.

### 5.5 Expected Shortfall (CVaR / Conditional Value at Risk)

Expected Shortfall (ES) addresses VaR's shortcomings by measuring the average loss in the worst cases:

```
ES_alpha = CVaR_alpha = E[Loss | Loss > VaR_alpha]
```

For a continuous loss distribution with CDF F:

```
ES_alpha = (1 / (1-alpha)) * integral_{alpha}^{1} VaR_u du
```

**Why CVaR is superior for options portfolios**:

1. **Coherent risk measure**: CVaR satisfies subadditivity (portfolio risk <= sum of individual risks), which VaR does not. This means VaR can paradoxically show that diversification increases risk, while CVaR correctly captures diversification benefits.

2. **Captures tail severity**: CVaR tells you HOW BAD things get when they go wrong, not just the threshold. For short gamma strategies, the tail losses can be 3-5x the VaR.

3. **Convex optimization**: CVaR can be minimized using linear programming (Rockafellar and Uryasev, 2000), making portfolio optimization tractable.

4. **Regulatory acceptance**: CVaR (under the name "Expected Shortfall") has replaced VaR as the primary risk metric in Basel III banking regulations.

---

## 6. The Sharpe Ratio and Its Limitations for Options

### 6.1 The Sharpe Ratio

```
Sharpe = (R_p - R_f) / sigma_p
```

where R_p is portfolio return, R_f is risk-free rate, sigma_p is portfolio standard deviation.

The Sharpe ratio measures excess return per unit of total volatility. It is the most widely used risk-adjusted return metric.

### 6.2 Why Sharpe Is Misleading for Options Strategies

**The fundamental problem**: Sharpe treats upside volatility and downside volatility identically. A strategy that generates consistent small gains with occasional catastrophic losses will show a HIGH Sharpe ratio -- until the catastrophe occurs.

**Short volatility strategies and Sharpe inflation**:
- Selling OTM puts: Sharpe of 1.0-2.0 in normal markets, then -5.0 in a crash
- Iron condors: High Sharpe because most months are small gains
- Covered calls: Artificially high Sharpe because upside is capped

This is the "picking up pennies in front of a steamroller" problem. The strategy harvests small, consistent profits (making sigma look low) while hiding catastrophic tail risk that standard deviation fails to capture.

**Mathematical problem**: Sharpe assumes returns are normally distributed (or at least symmetrically distributed). Options strategies produce returns with:
- Negative skewness (short gamma strategies): more frequent small gains, rare large losses
- Positive skewness (long gamma strategies): frequent small losses, rare large gains
- Excess kurtosis (fat tails): extreme outcomes more likely than normal distribution predicts

### 6.3 Better Metrics for Options

**Sortino Ratio** -- penalizes only downside risk:

```
Sortino = (R_p - R_target) / sigma_downside
```

where sigma_downside = sqrt(E[min(R - R_target, 0)^2]). The Sortino ratio focuses only on the volatility traders actually fear -- downside deviations. Many institutional investors prefer it over Sharpe.

**Calmar Ratio** -- return relative to worst-case experience:

```
Calmar = Annualized_Return / Maximum_Drawdown
```

This directly measures how much pain (drawdown) you endured for your gains. A Calmar > 1.0 means your annualized return exceeds your worst drawdown. The limitation: if the backtest period does not include a major drawdown, the Calmar ratio looks unrealistically high.

**Omega Ratio** -- considers the full return distribution:

```
Omega(threshold) = integral_{threshold}^{infinity} (1 - F(r)) dr / integral_{-infinity}^{threshold} F(r) dr
```

The Omega ratio is the probability-weighted ratio of gains to losses relative to a threshold. It incorporates all moments of the distribution (mean, variance, skewness, kurtosis, and beyond) and is especially useful for evaluating portfolios with non-normal return distributions.

**Gain-to-Pain Ratio (GPR)** -- Jack Schwager's preferred metric:

```
GPR = Sum of all monthly returns / |Sum of all monthly losses|
```

Schwager considers the GPR more meaningful than the Sharpe ratio because it normalizes return by the actual losses required to achieve that return, not by variability. The GPR penalizes all losses in proportion to their size, while upside volatility only benefits the ratio.

**Benchmarks for GPR** (Schwager):
- 1.0: Acceptable
- 2.0: Outstanding
- 3.0: Excellent
- 4.0: World class

**Pain Ratio** -- return per unit of suffering:

```
Pain Ratio = Annualized Return / Pain Index
```

where the Pain Index measures the depth, duration, and frequency of drawdowns (not just the maximum).

### 6.4 Summary: Which Metric When?

| Metric | Best For | Weakness |
|---|---|---|
| Sharpe | Comparing symmetric strategies | Misleading for options |
| Sortino | Strategies with asymmetric risk | Ignores upside shape |
| Calmar | Drawdown-sensitive evaluation | Period-dependent |
| Omega | Full distribution comparison | Computationally intensive |
| GPR | Practitioner comparison | Requires 3+ years of data |
| Pain Ratio | Long-term evaluation | Less widely known |

---

## 7. Monte Carlo Simulation for Options Portfolios

### 7.1 Generating Correlated Price Paths

**Cholesky Decomposition**: The standard method for generating correlated multivariate normal random variables.

Given N assets with covariance matrix Sigma:

1. Compute the Cholesky decomposition: Sigma = L * L^T, where L is lower-triangular
2. Generate N independent standard normal random variables: Z = (Z_1, ..., Z_N)
3. Compute correlated returns: R = mu + L * Z

This ensures the simulated returns have the correct mean vector and covariance structure.

**For options-specific simulations**: Use Geometric Brownian Motion (GBM) for each asset:

```
S_i(t + dt) = S_i(t) * exp((mu_i - sigma_i^2/2)*dt + sigma_i * sqrt(dt) * epsilon_i)
```

where the epsilon_i are generated via Cholesky decomposition to be properly correlated.

**Beyond GBM**: For more realistic option pricing:
- Stochastic volatility models (Heston, SABR): capture the vol smile
- Jump-diffusion models (Merton, Kou): capture sudden large moves
- Local volatility models (Dupire): calibrate to the full implied vol surface

### 7.2 Variance Reduction Techniques

**Antithetic Variates**: For each simulated path with random draws Z, also simulate the path with -Z. The estimate becomes:

```
theta_hat = (1/2) * [f(Z) + f(-Z)]
```

The variance of this estimator is:

```
Var[theta_hat] = (1/2) * Var[f(Z)] * (1 + Corr[f(Z), f(-Z)])
```

Since f(Z) and f(-Z) are typically negatively correlated (when one path goes up, the mirrored path goes down), the variance is reduced. Antithetic variates are most effective when f is close to linear; they eliminate all variance for perfectly linear payoffs.

**Control Variates**: If you have a related quantity C with a known expected value E[C], use it to reduce variance:

```
theta_hat_CV = theta_hat - beta * (C_hat - E[C])
```

where beta = Cov(theta, C) / Var(C). For options pricing, the underlying stock price itself can serve as a control variate (since E[S_T] = S_0 * e^{rT} is known).

**Stratified Sampling**: Divide the probability space into strata and sample proportionally from each, ensuring the tails are adequately represented.

**Importance Sampling**: Oversample from the tail of the distribution (where the rare but important events occur) and reweight. Particularly useful for estimating probabilities of extreme losses.

### 7.3 Practical Implementation Considerations

**Number of simulations needed**:
- For option pricing: 10,000-100,000 paths typically sufficient
- For VaR/CVaR at 99%: need 100,000+ paths for stable estimates
- For portfolio optimization: 50,000+ paths recommended
- Standard error scales as 1/sqrt(N), so quadrupling simulations halves the error

**Computational cost**: The bottleneck is repricing options at each time step. For a portfolio with P positions, T time steps, and N simulations:
- Total option repricings: P * T * N
- For P=50, T=252 (daily), N=100,000: 1.26 billion repricings
- Mitigation: use delta-gamma approximation for intermediate steps, full repricing only at key dates

### 7.4 Using Monte Carlo For Key Decisions

1. **Position sizing optimization**: Simulate portfolio evolution at various position sizes, find the size that maximizes risk-adjusted growth (essentially numerical Kelly for complex portfolios).

2. **Strategy comparison**: Run identical market simulations through different strategies and compare distributions of outcomes (growth rate, max drawdown, Sharpe, CVaR).

3. **Stress testing**: Inject historical scenarios (2008 GFC, 2020 COVID crash, 2022 rate shock) into simulations and measure portfolio impact.

4. **Optimal exit rules**: Simulate strategies with different exit triggers (50% profit, 200% loss, 21 DTE roll) and find which rules maximize risk-adjusted returns.

---

## 8. Systematic Strategy Evaluation

### 8.1 Backtest Design for Options Strategies

**Unique challenges**:
- Options data is expensive and complex (need full chains with Greeks)
- Greeks change daily, requiring daily recomputation
- Early exercise risk for American options
- Corporate actions (splits, dividends) affect strike prices
- Liquidity varies drastically across strikes and expirations

**Critical biases to avoid**:

1. **Survivorship bias**: Ignoring delisted underlyings inflates backtest returns. One momentum strategy study found that survivorship bias inflated CAGR from 12.2% to 26% -- the "excess alpha" was almost entirely fake. Always include failed and delisted companies.

2. **Look-ahead bias**: Using information not available at the time of the trade decision. Common examples: using realized volatility to size positions (you only know historical vol at decision time), using final earnings data before earnings are reported, selecting underlyings based on future performance.

3. **Transaction cost modeling**: Options have wide bid-ask spreads (often 5-20% of the option value for less liquid strikes). Realistic backtests must include:
   - Bid-ask spread (assume fill at mid only for very liquid options)
   - Slippage (market impact for larger orders)
   - Commissions and fees
   - Assignment/exercise fees

4. **Selection bias / data mining bias**: Testing 100 strategy variations and reporting the best one. With 100 independent tests at the 5% significance level, you expect 5 "significant" results by pure chance.

### 8.2 Statistical Significance

**Minimum sample size**: A baseline of 30 trades provides minimal statistical testing capability, but 100+ trades are recommended for meaningful inference.

**Key statistical tests**:
- **T-test**: Is the mean return significantly different from zero?
  - t = mean(R) / (std(R) / sqrt(n))
  - Require p-value < 0.05 (or preferably < 0.01)

- **Bootstrap significance**: Resample trades with replacement (10,000+ iterations), compute the strategy metric on each resample, construct confidence intervals. If the 95% CI excludes zero, the result is significant.

- **Monte Carlo permutation test**: Randomly shuffle trade entry times (breaking the connection between signal and outcome), recompute strategy returns. Compare actual returns to the distribution of shuffled returns.

**The multiple comparisons problem**: When evaluating K strategy variants:
- Bonferroni correction: use significance level alpha/K instead of alpha
- False Discovery Rate (Benjamini-Hochberg): less conservative, controls the expected proportion of false discoveries
- A priori hypothesis: define the strategy before looking at the data (the strongest protection)

**Practical rule**: If you tested 20 variations and found one with p = 0.04, it is NOT significant (expected false positives: 20 * 0.05 = 1). You need p < 0.05/20 = 0.0025 (Bonferroni) or strong out-of-sample confirmation.

### 8.3 Walk-Forward Analysis

Walk-forward analysis is now considered the "gold standard" in trading strategy validation. The process:

1. **In-sample (training) period**: Optimize strategy parameters on historical data
2. **Out-of-sample (testing) period**: Test the optimized parameters on unseen future data
3. **Roll forward**: Move both windows forward in time and repeat
4. **Aggregate**: Combine all out-of-sample results for the final performance assessment

**Key design choices**:
- In-sample window: typically 2-5 years for options strategies
- Out-of-sample window: typically 6-12 months
- Overlap: none (strict rolling) or some overlap for more data points
- Reoptimization frequency: quarterly or semi-annually

**Pitfalls**:
- **Meta-overfitting**: Optimizing the walk-forward process itself (adjusting window sizes, fitness functions, parameter ranges) until results look good -- this defeats the entire purpose
- **Sparse data**: Options strategies may generate only 5-10 trades per out-of-sample window, making individual windows statistically meaningless
- **Regime changes**: A strategy optimized on 2015-2019 data may fail spectacularly in 2020's volatility regime

---

## 9. Risk Management Rules -- What Works

### 9.1 Position-Level Rules

**Maximum risk per position**: 1-5% of account (standard across practitioners):
- 1% for undefined risk (naked options, ratio spreads)
- 2-3% for defined risk (vertical spreads, iron condors)
- 5% for very high-conviction, defined-risk trades only
- "Max risk" = max possible loss on the position, not premium spent

**Strategy-specific guidelines**:
- **Defined risk** (spreads): Max loss clearly defined. Position size = Account * f% / Max_Loss_Per_Contract
- **Undefined risk** (naked options): Use margin requirement as proxy for risk, but also consider tail scenarios (e.g., 2x the expected move)
- For undefined-risk strategies, maintain at least 40% of funds unutilized for adjustments and margin expansion

**Exit rules** (three types):
1. **P&L-based**: Close at 50% profit or 200% loss (common for credit strategies)
2. **Time-based**: Close at 21 DTE regardless of P&L (avoid gamma risk near expiration)
3. **Delta-based**: Close when short strike delta exceeds a threshold (e.g., 30-delta ITM breach)

### 9.2 Portfolio-Level Rules

**Total capital at risk**: Maximum 20-30% of account at risk at any given time. This means the sum of maximum losses across all positions should not exceed 20-30% of the account.

**Correlation-adjusted exposure limits**: If you have 3 positions in tech stocks, treat them as partially one position for risk purposes (reduce combined size by the correlation factor).

**Daily loss limits**: Stop opening new positions if the portfolio is down X% for the day (e.g., 3-5%). This prevents tilt-driven over-trading after losses.

**Theta targeting**: For premium-selling portfolios, limit daily theta collection to 0.1-0.3% of account value. More theta means more gamma risk.

**Sector diversification**: No more than 20-25% of risk in a single sector. No more than 10% in a single underlying.

### 9.3 Strategy-Level Rules

**Balance**: Maintain a mix of:
- Positive theta strategies (credit spreads, iron condors): income generation
- Negative theta strategies (long options, debit spreads): tail protection
- Delta-neutral strategies (straddles, calendars): volatility plays
- The mix should shift based on implied volatility regime (sell premium when IV is high, buy protection when IV is low)

**Directional balance**: Limit the number of same-direction positions. If you have 5 bullish positions and 0 bearish ones, you are not diversified -- you are making a directional bet.

**Expiration diversification**: Spread positions across multiple expiration cycles to avoid having all positions expire in the same week (where gamma risk is highest and a single adverse move can damage the entire portfolio simultaneously).

### 9.4 Position Sizing Formula Summary

**For a defined-risk options trade**:

```
Number of contracts = (Account_Size * Kelly_fraction * Fractional_Kelly) / Max_Loss_Per_Contract
```

Where:
- Account_Size = total account value
- Kelly_fraction = (EV / Max_Loss) from the adapted Kelly formula
- Fractional_Kelly = 0.25 to 0.50 (based on confidence in edge)
- Max_Loss_Per_Contract = width of spread - credit received (times 100 for equity options)

**Cross-check against position limits**:
- Result must not exceed 5% of account in max risk
- Combined with existing positions, must not exceed 25% total capital at risk
- Must not create excessive sector concentration

---

## 10. Behavioral Risk Management

### 10.1 Common Behavioral Biases in Position Sizing

**Overconfidence bias**: The tendency to overestimate one's ability to predict outcomes. In trading, this manifests as:
- Sizing up after a winning streak ("I'm on fire, let me double the position")
- Ignoring stop-loss rules because "I know this trade will work"
- Research shows the most active traders earned 11.4% annually vs 18.5% for the least active -- overconfidence-driven overtrading destroys returns

**Gambler's fallacy**: The mistaken belief that past random events affect future probabilities:
- "I've had 5 losing trades in a row, I'm due for a win" (false -- each trade is independent)
- Leads to martingale-like behavior: doubling down after losses
- The market has no memory of your cost basis

**Anchoring bias**: Fixating on a reference point that distorts decision-making:
- Refusing to close a losing trade because "it was at $50 last month" (irrelevant)
- Sizing positions based on what you "usually" trade rather than current conditions
- Averaging down without new information (anchoring to entry price)

**Disposition effect**: Selling winners too early and holding losers too long:
- Driven by loss aversion (losses hurt ~2x as much as equivalent gains feel good)
- Directly opposes the "let winners run, cut losers short" principle
- Can be countered with systematic exit rules

**Recency bias**: Overweighting recent experience in probability estimates:
- After a market crash: over-sizing hedges, under-sizing risk-on trades
- After a calm period: under-sizing hedges, over-sizing short gamma trades
- Kelly estimates based on recent data only can be dangerously wrong

### 10.2 The "Game Over" Risk

The single most important concept in risk management: **permanent loss of capital that ends your ability to trade**.

**Mathematical framing**: Kelly theory shows that betting f > 2*f* leads to guaranteed ruin in the long run. But even at f = f*, severe drawdowns are possible. The "game over" threshold is the drawdown level from which recovery is either impossible or takes so long that it is functionally equivalent to ruin.

**Rules to prevent "game over" events**:

1. **Never risk more than you can afford to lose on ANY single trade**. Even a "guaranteed" trade can go wrong (assignment risk, flash crash, exchange halt, counterparty failure).

2. **Use defined-risk strategies by default**. Undefined risk strategies (naked calls, ratio spreads) can produce losses that exceed your account value. Defined-risk strategies have a known maximum loss.

3. **Maintain a disaster reserve**. Keep 50-70% of your account in cash or cash equivalents at all times. This is your "survival capital."

4. **Diversify across time**. Don't put all your positions on at once. Scale in over weeks to avoid catching a single adverse event with full exposure.

5. **Have a hard stop**. If the account drops 20% in a single month, stop trading and reassess. No strategy, no conviction, no edge is worth the risk of a 50%+ drawdown.

### 10.3 Psychological Capital Management

**The "stomach test"**: If a position size would keep you awake at night, it is too large -- regardless of what Kelly says. Psychological capital (the ability to think clearly and execute the plan) is as important as financial capital.

**Sizing for sustainability**:
- Position sizes should be small enough that a maximum loss on any single trade does not emotionally affect the next trade
- If you find yourself "needing" a trade to win, you are sized too large
- The goal is to make each trade feel like one of thousands -- insignificant individually, significant in aggregate

**Progressive sizing**: Start new strategies at quarter-Kelly or smaller. Increase size only after demonstrating a positive track record with sufficient sample size (50+ trades minimum). This builds both statistical confidence and psychological comfort.

---

## Appendix A: Key Formulas Reference

### Kelly Criterion Variants

| Context | Formula | Notes |
|---|---|---|
| Binary bet | f* = (bp - q) / b | b=odds, p=P(win), q=1-p |
| Credit spread | f* = (C*P_w - (W-C)*P_l) / (W-C) | C=credit, W=width |
| Continuous (Gaussian) | f* = (mu - r) / sigma^2 | mu=return, sigma=vol, r=risk-free |
| Multi-asset | f* = Sigma^{-1} * (mu - r*1) | Sigma=covariance matrix |
| Half-Kelly | f = f*/2 | 75% of optimal growth, ~50% less drawdown |
| Drawdown-constrained | solve max E[log(W)] s.t. P(DD>d)<p | Busseti et al. (2016) |

### Risk Metrics

| Metric | Formula | Use Case |
|---|---|---|
| VaR_alpha | P(Loss > VaR) = 1 - alpha | Point estimate of tail risk |
| CVaR_alpha | E[Loss \| Loss > VaR_alpha] | Average tail risk (coherent) |
| Delta-Gamma P&L | dP = delta*dS + 0.5*Gamma*dS^2 | Options portfolio approximation |
| Sharpe | (R - Rf) / sigma(R) | Symmetric risk-adjusted return |
| Sortino | (R - Rt) / sigma_down | Downside risk-adjusted return |
| Calmar | Ann_Return / Max_Drawdown | Return per unit of worst loss |
| GPR | Sum(profits) / \|Sum(losses)\| | Schwager's preferred metric |

### Drawdown Recovery Table

| Drawdown | Required Gain | Years at 15% CAGR |
|---|---|---|
| 10% | 11.1% | 0.75 |
| 20% | 25.0% | 1.6 |
| 30% | 42.9% | 2.6 |
| 50% | 100.0% | 5.0 |
| 75% | 300.0% | 10.5 |

---

## Appendix B: Recommended Reading

### Academic Foundations
- **Kelly, J.L. (1956)**: "A New Interpretation of Information Rate" -- the original paper
- **Breiman, L. (1961)**: "Optimal Gambling Systems for Favorable Games" -- rigorous proofs of Kelly optimality
- **Merton, R. (1969)**: "Lifetime Portfolio Selection Under Uncertainty: The Continuous-Time Case"
- **Merton, R. (1971)**: "Optimum Consumption and Portfolio Rules in a Continuous-Time Model"
- **Markowitz, H. (1952)**: "Portfolio Selection" -- the foundation of modern portfolio theory
- **Cover, T. & Thomas, J. (1991)**: "Elements of Information Theory" -- Chapter 16 on gambling and data compression
- **Thorp, E.O. (1975)**: "Portfolio Choice and the Kelly Criterion"
- **Busseti, E., Ryu, E.K., Boyd, S. (2016)**: "Risk-Constrained Kelly Gambling"
- **Peters, O. (2019)**: "The Ergodicity Problem in Economics" (Nature Physics)
- **Rockafellar, R.T. & Uryasev, S. (2000)**: "Optimization of Conditional Value-at-Risk"

### Practitioner Books
- **Thorp, E.O. (1962)**: "Beat the Dealer" -- first application of Kelly to gambling
- **Thorp, E.O. & Kassouf, S. (1967)**: "Beat the Market" -- Kelly applied to warrants
- **Vince, R. (1990)**: "Portfolio Management Formulas" -- Optimal f and position sizing
- **Vince, R. (1992)**: "The Mathematics of Money Management"
- **Van Tharp (1998)**: "Trade Your Way to Financial Freedom" -- position sizing systems
- **Poundstone, W. (2005)**: "Fortune's Formula" -- accessible history of Kelly criterion
- **Schwager, J. (2012)**: "Hedge Fund Market Wizards" -- Gain-to-Pain ratio and practitioner insights

---

## Appendix C: Sources and References

### Web Sources Consulted
- [Kelly Criterion Wikipedia](https://en.wikipedia.org/wiki/Kelly_criterion)
- [Gambling and Information Theory Wikipedia](https://en.wikipedia.org/wiki/Gambling_and_information_theory)
- [Thorp - The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market (2007)](https://web.williams.edu/Mathematics/sjmiller/public_html/341/handouts/Thorpe_KellyCriterion2007.pdf)
- [Thorp - Portfolio Choice and the Kelly Criterion (1975)](https://gwern.net/doc/statistics/decision/1975-thorp.pdf)
- [Good and Bad Properties of the Kelly Criterion (Aldous)](https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf)
- [Frontiers - Practical Implementation of the Kelly Criterion](https://www.frontiersin.org/journals/applied-mathematics-and-statistics/articles/10.3389/fams.2020.577050/full)
- [Busseti, Ryu, Boyd - Risk-Constrained Kelly Gambling (Stanford)](https://stanford.edu/~boyd//papers/pdf/kelly.pdf)
- [Fractional Kelly Strategies in Continuous Time (Davis, Lleo)](https://him-application.uni-bonn.de/uploads/media/DavisLleoKellyChapter.pdf)
- [Kelly Criterion for Option Investment (Georgia Tech)](https://shenk.math.gatech.edu/OptionsClub/kellyOptionTalk1.pdf)
- [Kelly Criterion for Position Sizing Credit Spreads](https://www.stockmarketoptionstrading.com/episode/kelly-criterion-for-position-sizing-credit-spreads)
- [QuantPedia - Beware of Excessive Leverage: Kelly and Optimal F](https://quantpedia.com/beware-of-excessive-leverage-introduction-to-kelly-and-optimal-f/)
- [The Kelly Criterion, Capital Market Parabola, and the Sharpe Ratio (Outcast Beta)](https://outcastbeta.com/the-kelly-criterion-capital-market-parabola-the-almighty-sharpe-ratio/)
- [Kelly Criterion in the Presence of Uncertainty About Risk (Outcast Beta)](https://outcastbeta.com/the-kelly-criterion-in-the-presence-of-uncertainty-about-risk/)
- [Why Fractional Kelly? Simulations of Bet Size with Uncertainty (Matthew Downey)](https://matthewdowney.github.io/uncertainty-kelly-criterion-optimal-bet-size.html)
- [Risk-Constrained Kelly Criterion: Foundations to Trading (QuantInsti)](https://blog.quantinsti.com/risk-constrained-kelly-criterion/)
- [Kelly Criterion: From a Simple Random Walk to Levy Processes (USC)](https://dornsife.usc.edu/sergey-lototsky/wp-content/uploads/sites/211/2023/11/Kelly-Fin-SIFIN-Final.pdf)
- [Kelly's Criterion in Portfolio Optimization: A Decoupled Problem (arXiv)](https://arxiv.org/pdf/1710.00431)
- [Bayesian Kelly Criterion (Columbia Business School)](https://business.columbia.edu/sites/default/files-efs/pubfiles/6343/bayes_kelly.pdf)
- [Ergodicity Economics Wikipedia](https://en.wikipedia.org/wiki/Ergodicity_economics)
- [Peters (2019) - The Ergodicity Problem in Economics (Nature Physics)](https://www.nature.com/articles/s41567-019-0732-0)
- [Expected Shortfall Wikipedia](https://en.wikipedia.org/wiki/Expected_shortfall)
- [Delta-Gamma VaR: Implementing the Quadratic Portfolio Model](https://www.sciencedirect.com/science/article/abs/pii/S0377221702007828)
- [Correlated Monte Carlo Simulation using Cholesky Decomposition (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4066115)
- [Gain-to-Pain Ratio (Wall Street Mojo)](https://www.wallstreetmojo.com/gain-to-pain-ratio/)
- [Pain Ratio (Swan Global Investments)](https://www.swanglobalinvestments.com/pain-ratio-better-risk-return-measure/)
- [Walk-Forward Optimization (QuantInsti)](https://blog.quantinsti.com/walk-forward-optimization-introduction/)
- [Kelly Criterion vs Optimal F (Quantified Strategies)](https://www.quantifiedstrategies.com/kelly-criterion-vs-optimal-f/)
- [Optimal f Money Management (Quantified Strategies)](https://www.quantifiedstrategies.com/optimal-f-money-management/)
