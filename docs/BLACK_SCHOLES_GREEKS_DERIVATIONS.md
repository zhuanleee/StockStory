# Complete Mathematical Derivations of Option Greeks from Black-Scholes

## Table of Contents
1. [Notation and Preliminaries](#1-notation-and-preliminaries)
2. [Black-Scholes Closed-Form Derivation](#2-black-scholes-closed-form-derivation)
3. [Critical Identity for Greeks Computations](#3-critical-identity-for-greeks-computations)
4. [First-Order Greeks](#4-first-order-greeks)
5. [Second-Order Greeks](#5-second-order-greeks)
6. [Third-Order Greeks](#6-third-order-greeks)
7. [The Theta-Gamma Relationship (Deep Dive)](#7-the-theta-gamma-relationship)
8. [Greeks for Multi-Leg Strategies](#8-greeks-for-multi-leg-strategies)
9. [Greeks Under Different Models](#9-greeks-under-different-models)
10. [Summary Formula Sheet](#10-summary-formula-sheet)

---

## 1. Notation and Preliminaries

### 1.1 Variables and Constants

| Symbol | Definition |
|--------|-----------|
| S | Current price of the underlying asset |
| K | Strike price of the option |
| T | Time to expiration (in years). We use tau = T - t where t is current time |
| r | Continuously compounded risk-free interest rate |
| q | Continuous dividend yield (set q = 0 for non-dividend-paying stocks) |
| sigma | Volatility of the underlying asset (annualized) |
| C | European call option price |
| P | European put option price |
| V | Generic option price (call or put) |

### 1.2 Standard Normal Functions

The standard normal probability density function (PDF):

    n(x) = (1 / sqrt(2*pi)) * exp(-x^2 / 2)

The cumulative standard normal distribution function (CDF):

    N(x) = integral from -infinity to x of n(u) du

Key properties of n(x):
- n'(x) = -x * n(x)  (derivative of PDF)
- n(x) > 0 for all x
- n(-x) = n(x)  (symmetry)
- N(-x) = 1 - N(x)  (symmetry of CDF)
- N'(x) = n(x)

### 1.3 The d1 and d2 Parameters

    d1 = [ln(S/K) + (r - q + sigma^2/2) * T] / (sigma * sqrt(T))

    d2 = d1 - sigma * sqrt(T)
       = [ln(S/K) + (r - q - sigma^2/2) * T] / (sigma * sqrt(T))

Key partial derivatives of d1 and d2 (used repeatedly in Greeks derivations):

    dd1/dS = 1 / (S * sigma * sqrt(T))
    dd2/dS = 1 / (S * sigma * sqrt(T))          [same as dd1/dS since d2 = d1 - sigma*sqrt(T)]

    dd1/dsigma = -d2 / sigma = (-d1 + sigma*sqrt(T)) / sigma = sqrt(T) - d1/sigma
    dd2/dsigma = -d1 / sigma

    dd1/dT = -(d1 / (2T)) + (r - q + sigma^2/2) / (sigma * sqrt(T))
           = [-(r - q)/(sigma*sqrt(T))] + sigma/(2*sqrt(T))  ... [alternative form]

    dd1/dr = sqrt(T) / sigma
    dd2/dr = sqrt(T) / sigma

Note: Throughout this document, T denotes time to expiration. When we write dV/dt (theta), this is the derivative with respect to calendar time t, which satisfies dV/dt = -dV/dT (since T = T_expiry - t). We adopt the convention that theta = dV/dt = -dV/dT.

---

## 2. Black-Scholes Closed-Form Derivation

### 2.1 Geometric Brownian Motion (GBM)

The underlying asset price S(t) follows:

    dS = mu * S * dt + sigma * S * dW

where:
- mu is the drift (expected return)
- sigma is the volatility
- W(t) is a standard Brownian motion (Wiener process)

This is a stochastic differential equation (SDE). By Ito's formula, if we set X = ln(S):

    dX = (mu - sigma^2/2) dt + sigma dW

so ln(S) is a Brownian motion with drift. The solution is:

    S(t) = S(0) * exp((mu - sigma^2/2)*t + sigma*W(t))

meaning S(t) is log-normally distributed.

### 2.2 Ito's Lemma Applied to V(S, t)

Let V(S, t) be a twice-differentiable function of S and t. By Ito's Lemma:

    dV = (dV/dt) dt + (dV/dS) dS + (1/2)(d^2V/dS^2)(dS)^2

Substituting dS = mu*S*dt + sigma*S*dW and using (dS)^2 = sigma^2 * S^2 * dt (by Ito calculus rules: dt*dt = 0, dt*dW = 0, dW*dW = dt):

    dV = [dV/dt + mu*S*(dV/dS) + (1/2)*sigma^2*S^2*(d^2V/dS^2)] dt + sigma*S*(dV/dS) dW

### 2.3 Delta-Hedged Portfolio Construction

Construct a portfolio Pi consisting of one option and Delta shares of the underlying (short):

    Pi = V - Delta * S

where Delta = dV/dS. The change in portfolio value over dt:

    dPi = dV - (dV/dS) * dS

Substituting the Ito expansion:

    dPi = [dV/dt + mu*S*(dV/dS) + (1/2)*sigma^2*S^2*(d^2V/dS^2)] dt + sigma*S*(dV/dS) dW
          - (dV/dS) * [mu*S*dt + sigma*S*dW]

The stochastic terms (dW terms) cancel:

    dPi = [dV/dt + (1/2)*sigma^2*S^2*(d^2V/dS^2)] dt

This portfolio is **instantaneously riskless** -- it contains no dW term.

### 2.4 No-Arbitrage Argument and the BSM PDE

A riskless portfolio must earn the risk-free rate r. Therefore:

    dPi = r * Pi * dt = r * (V - (dV/dS)*S) * dt

Setting the two expressions for dPi equal:

    dV/dt + (1/2)*sigma^2*S^2*(d^2V/dS^2) = r*V - r*S*(dV/dS)

Rearranging gives the **Black-Scholes-Merton PDE**:

    dV/dt + (1/2)*sigma^2*S^2*(d^2V/dS^2) + r*S*(dV/dS) - r*V = 0

With dividend yield q, this generalizes to:

    dV/dt + (1/2)*sigma^2*S^2*(d^2V/dS^2) + (r - q)*S*(dV/dS) - r*V = 0

**Key observation**: The drift mu has vanished entirely. The option price does not depend on the expected return of the stock -- only on r, sigma, and the other observable parameters. This is the essence of risk-neutral pricing.

### 2.5 Boundary Conditions

For a European call with strike K and expiry T:
- Terminal condition: C(S, T) = max(S - K, 0)
- Boundary as S -> 0: C(0, t) = 0
- Boundary as S -> infinity: C(S, t) ~ S*e^(-q*T) - K*e^(-r*T)

For a European put:
- Terminal condition: P(S, T) = max(K - S, 0)
- Boundary as S -> 0: P(0, t) = K*e^(-r*(T-t))
- Boundary as S -> infinity: P(S, t) -> 0

### 2.6 Solution via Transformation to Heat Equation

**Step 1: Change of variables.** Let tau = T - t (time to expiry), and set:

    x = ln(S/K) + (r - q - sigma^2/2)*tau
    u(x, tau) = e^(r*tau) * V(S, t)

Under this transformation, the BSM PDE becomes the **heat equation**:

    du/dtau = (sigma^2 / 2) * d^2u/dx^2

with initial condition at tau = 0 determined by the payoff.

**Step 2: Solve the heat equation.** The fundamental solution (Green's function) of the heat equation is:

    G(x, tau) = (1 / sqrt(2*pi*sigma^2*tau)) * exp(-x^2 / (2*sigma^2*tau))

The solution is the convolution of the initial condition with the Green's function.

**Step 3: Evaluate the integral.** For a call option, the initial condition is u(x, 0) = max(K*e^x - K, 0) = K*max(e^x - 1, 0). Working through the convolution integral and transforming back to original variables yields the closed-form solution.

### 2.7 The Black-Scholes Closed-Form Solution

**European Call Price (with continuous dividends):**

    C = S * e^(-q*T) * N(d1) - K * e^(-r*T) * N(d2)

**European Put Price (with continuous dividends):**

    P = K * e^(-r*T) * N(-d2) - S * e^(-q*T) * N(-d1)

**For non-dividend-paying stocks (q = 0):**

    C = S * N(d1) - K * e^(-r*T) * N(d2)
    P = K * e^(-r*T) * N(-d2) - S * N(-d1)

### 2.8 Put-Call Parity

The call and put prices satisfy:

    C - P = S * e^(-q*T) - K * e^(-r*T)

This can be verified directly from the formulas using N(d1) + N(-d1) = 1 and N(d2) + N(-d2) = 1.

---

## 3. Critical Identity for Greeks Computations

### 3.1 The Fundamental Simplification Lemma

**Lemma**: Under the Black-Scholes model:

    S * e^(-q*T) * n(d1) = K * e^(-r*T) * n(d2)

This identity is the single most important tool for simplifying all Greeks derivations. Without it, the formulas become extremely unwieldy.

**Proof:**

We need to show that:

    (S * e^(-q*T)) / (K * e^(-r*T)) = n(d2) / n(d1)

The left-hand side:

    (S/K) * e^((r-q)*T)

Now examine the right-hand side. Since n(x) = (1/sqrt(2*pi)) * exp(-x^2/2):

    n(d2)/n(d1) = exp(-(d2^2)/2 + (d1^2)/2) = exp((d1^2 - d2^2)/2)

Compute d1^2 - d2^2:

    d1^2 - d2^2 = (d1 - d2)(d1 + d2)

Since d1 - d2 = sigma*sqrt(T):

    d1^2 - d2^2 = sigma*sqrt(T) * (d1 + d2)

Now d1 + d2 = 2*d1 - sigma*sqrt(T):

    d1 + d2 = 2*[ln(S/K) + (r - q + sigma^2/2)*T] / (sigma*sqrt(T)) - sigma*sqrt(T)
            = [2*ln(S/K) + 2*(r-q)*T + sigma^2*T - sigma^2*T] / (sigma*sqrt(T))
            = [2*ln(S/K) + 2*(r-q)*T] / (sigma*sqrt(T))

Therefore:

    d1^2 - d2^2 = sigma*sqrt(T) * [2*ln(S/K) + 2*(r-q)*T] / (sigma*sqrt(T))
                = 2*ln(S/K) + 2*(r-q)*T

So:

    n(d2)/n(d1) = exp([2*ln(S/K) + 2*(r-q)*T] / 2)
                = exp(ln(S/K) + (r-q)*T)
                = (S/K) * e^((r-q)*T)

This equals the left-hand side, completing the proof. QED.

### 3.2 Consequence for Derivatives

When differentiating the BSM formula, terms of the form:

    S * e^(-q*T) * n(d1) * (dd1/dx) - K * e^(-r*T) * n(d2) * (dd2/dx)

arise for various variables x. Since dd1/dx = dd2/dx for x in {S, r} (because d1 - d2 = sigma*sqrt(T) is independent of S and r), the lemma immediately gives:

    S * e^(-q*T) * n(d1) * (dd1/dx) - K * e^(-r*T) * n(d2) * (dd2/dx) = 0

This massive cancellation is what makes the Greeks formulas so elegant.

---

## 4. First-Order Greeks

### 4.1 Delta: dV/dS

#### 4.1.1 Derivation for European Call

Starting from:

    C = S * e^(-q*T) * N(d1) - K * e^(-r*T) * N(d2)

Differentiate with respect to S using the product rule:

    dC/dS = e^(-q*T) * N(d1)
           + S * e^(-q*T) * n(d1) * (dd1/dS)
           - K * e^(-r*T) * n(d2) * (dd2/dS)

Since dd1/dS = dd2/dS = 1/(S*sigma*sqrt(T)), the last two terms become:

    [S * e^(-q*T) * n(d1) - K * e^(-r*T) * n(d2)] * dd1/dS

By the Fundamental Lemma (Section 3.1), S*e^(-q*T)*n(d1) = K*e^(-r*T)*n(d2), so this bracket is zero.

Therefore:

    **Delta_call = dC/dS = e^(-q*T) * N(d1)**

For q = 0: Delta_call = N(d1)

#### 4.1.2 Derivation for European Put

Starting from:

    P = K * e^(-r*T) * N(-d2) - S * e^(-q*T) * N(-d1)

Differentiate with respect to S:

    dP/dS = -K * e^(-r*T) * n(-d2) * (dd2/dS)
           - e^(-q*T) * N(-d1)
           + S * e^(-q*T) * n(-d1) * (dd1/dS)

Since n(-x) = n(x), the terms involving n(d1) and n(d2) again cancel by the Fundamental Lemma:

    **Delta_put = dP/dS = -e^(-q*T) * N(-d1) = e^(-q*T) * [N(d1) - 1]**

For q = 0: Delta_put = N(d1) - 1

**Verification via put-call parity**: From C - P = S*e^(-q*T) - K*e^(-r*T), differentiating:

    Delta_call - Delta_put = e^(-q*T)

Indeed: e^(-q*T)*N(d1) - e^(-q*T)*(N(d1) - 1) = e^(-q*T). Confirmed.

#### 4.1.3 Properties of Delta

- **Range**: For calls, Delta in (0, e^(-q*T)). For puts, Delta in (-e^(-q*T), 0).
- **ATM behavior**: When S = K*e^(-(r-q)*T) (forward ATM), d1 = sigma*sqrt(T)/2, so Delta_call ~ e^(-q*T) * N(sigma*sqrt(T)/2) ~ e^(-q*T) * 0.5 for small sigma*sqrt(T).
- **Moneyness dependence**: As S -> infinity, d1 -> infinity, N(d1) -> 1, so Delta_call -> e^(-q*T). As S -> 0, d1 -> -infinity, N(d1) -> 0, so Delta_call -> 0.
- **Volatility dependence**: Higher sigma flattens the delta curve (sigmoid shape becomes less steep).
- **Time dependence**: As T -> 0, the delta curve approaches a step function: Delta -> e^(-q*T) for ITM calls, Delta -> 0 for OTM calls.
- **Probabilistic interpretation**: e^(q*T) * Delta_call = N(d1) is the probability that S(T) > K under the measure where the stock is the numeraire (the "share measure"). N(d2) is the risk-neutral probability that S(T) > K.

### 4.2 Vega: dV/dsigma

#### 4.2.1 Derivation

Differentiate the call price with respect to sigma:

    dC/dsigma = S * e^(-q*T) * n(d1) * (dd1/dsigma) - K * e^(-r*T) * n(d2) * (dd2/dsigma)

The partial derivatives of d1 and d2 with respect to sigma:

    dd1/dsigma = -d2/sigma   (since d1 = d2 + sigma*sqrt(T), differentiate: dd1/dsigma = dd2/dsigma + sqrt(T))
    dd2/dsigma = -d1/sigma   (differentiate d2 = [ln(S/K) + (r-q-sigma^2/2)*T]/(sigma*sqrt(T)))

To verify dd2/dsigma: Write d2 = [ln(S/K) + (r-q)*T]/(sigma*sqrt(T)) - sigma*sqrt(T)/2.

    dd2/dsigma = -[ln(S/K) + (r-q)*T]/(sigma^2 * sqrt(T)) - sqrt(T)/2
               = -(1/sigma)*{[ln(S/K) + (r-q)*T]/(sigma*sqrt(T)) + sigma*sqrt(T)/2}
               = -d1/sigma

And dd1/dsigma = dd2/dsigma + sqrt(T) = -d1/sigma + sqrt(T) = (-d1 + sigma*sqrt(T))/sigma = -d2/sigma. Confirmed.

Substituting:

    dC/dsigma = S*e^(-q*T)*n(d1)*(-d2/sigma) - K*e^(-r*T)*n(d2)*(-d1/sigma)
              = (1/sigma) * [-S*e^(-q*T)*n(d1)*d2 + K*e^(-r*T)*n(d2)*d1]

Applying the Fundamental Lemma (S*e^(-q*T)*n(d1) = K*e^(-r*T)*n(d2) = A, say):

    dC/dsigma = (A/sigma) * [-d2 + d1] = (A/sigma) * sigma * sqrt(T) = A * sqrt(T)

Therefore:

    **Vega = dC/dsigma = S * e^(-q*T) * n(d1) * sqrt(T) = K * e^(-r*T) * n(d2) * sqrt(T)**

For q = 0: Vega = S * n(d1) * sqrt(T)

#### 4.2.2 Vega is the Same for Calls and Puts

From put-call parity: C - P = S*e^(-q*T) - K*e^(-r*T). Differentiating with respect to sigma: dC/dsigma - dP/dsigma = 0.

Therefore Vega_call = Vega_put. This is a direct consequence of put-call parity.

#### 4.2.3 Properties of Vega

- **Always positive**: Since n(d1) > 0, sqrt(T) > 0, S > 0, vega is always positive. Higher volatility increases option value (both calls and puts).
- **ATM maximum**: Vega is maximized when d1 = 0 (since n(d1) is maximized at d1 = 0), which occurs near ATM.
- **Vega term structure**: Vega = S*e^(-q*T)*n(d1)*sqrt(T). For ATM options (d1 ~ 0), Vega ~ S*n(0)*sqrt(T) = S*sqrt(T)/(sqrt(2*pi)). So ATM vega scales as sqrt(T) -- longer-dated options have more vega.
- **Normalized (unit) vega**: Vega per 1% vol = Vega/100. Sometimes practitioners use "vega per unit of vol" = Vega, or "vega per basis point" = Vega/10000.
- **Vega convexity**: The rate at which vega itself changes with vol is volga (Section 5.3).

### 4.3 Theta: dV/dt

#### 4.3.1 Derivation for European Call

This is the most algebraically involved first-order Greek. Differentiate:

    C = S * e^(-q*T) * N(d1) - K * e^(-r*T) * N(d2)

with respect to T (noting theta = -dC/dT since theta = dC/dt and T = T_expiry - t):

    dC/dT = -q * S * e^(-q*T) * N(d1) + S * e^(-q*T) * n(d1) * (dd1/dT)
            + r * K * e^(-r*T) * N(d2) - K * e^(-r*T) * n(d2) * (dd2/dT)

The terms with n(d1) and n(d2): Since dd1/dT and dd2/dT differ only by d(sigma*sqrt(T))/dT = sigma/(2*sqrt(T)):

    dd1/dT = dd2/dT + sigma/(2*sqrt(T))

By the Fundamental Lemma, S*e^(-q*T)*n(d1) = K*e^(-r*T)*n(d2) = A, so:

    S*e^(-q*T)*n(d1)*(dd1/dT) - K*e^(-r*T)*n(d2)*(dd2/dT)
    = A*(dd2/dT + sigma/(2*sqrt(T))) - A*(dd2/dT)
    = A * sigma/(2*sqrt(T))

Therefore:

    dC/dT = -q*S*e^(-q*T)*N(d1) + r*K*e^(-r*T)*N(d2) + S*e^(-q*T)*n(d1)*sigma/(2*sqrt(T))

Since theta = -dC/dT:

    **Theta_call = -S * e^(-q*T) * n(d1) * sigma / (2*sqrt(T)) - r*K*e^(-r*T)*N(d2) + q*S*e^(-q*T)*N(d1)**

For q = 0:

    Theta_call = -S * n(d1) * sigma / (2*sqrt(T)) - r * K * e^(-r*T) * N(d2)

#### 4.3.2 Derivation for European Put

By put-call parity or direct differentiation:

    **Theta_put = -S * e^(-q*T) * n(d1) * sigma / (2*sqrt(T)) + r*K*e^(-r*T)*N(-d2) - q*S*e^(-q*T)*N(-d1)**

For q = 0:

    Theta_put = -S * n(d1) * sigma / (2*sqrt(T)) + r * K * e^(-r*T) * N(-d2)

**Verification**: Theta_call - Theta_put = -r*K*e^(-r*T)*[N(d2) + N(-d2)] + q*S*e^(-q*T)*[N(d1) + N(-d1)]
= -r*K*e^(-r*T) + q*S*e^(-q*T). This matches d(C-P)/dt from put-call parity. Confirmed.

#### 4.3.3 Properties of Theta

- **Usually negative**: The first term -S*e^(-q*T)*n(d1)*sigma/(2*sqrt(T)) is always negative. For calls, the -r*K*e^(-r*T)*N(d2) term is also negative. So call theta is always negative (for q = 0).
- **Put theta can be positive**: For deep ITM puts, the +r*K*e^(-r*T)*N(-d2) term can dominate, making theta positive. A deep ITM European put can gain value as time passes because the present value of the strike payment increases.
- **Theta acceleration**: Theta becomes more negative as T -> 0 for ATM options, since sigma/(2*sqrt(T)) -> infinity. This is the "time decay acceleration" near expiry.
- **Per-day theta**: Theta/365 (or Theta/252 for trading days) gives the daily decay in option value.

### 4.4 Rho: dV/dr

#### 4.4.1 Derivation for European Call

Differentiate:

    C = S * e^(-q*T) * N(d1) - K * e^(-r*T) * N(d2)

with respect to r:

    dC/dr = S * e^(-q*T) * n(d1) * (dd1/dr) + T * K * e^(-r*T) * N(d2) - K * e^(-r*T) * n(d2) * (dd2/dr)

Since dd1/dr = dd2/dr = sqrt(T)/sigma:

    S*e^(-q*T)*n(d1)*(dd1/dr) - K*e^(-r*T)*n(d2)*(dd2/dr) = [S*e^(-q*T)*n(d1) - K*e^(-r*T)*n(d2)] * sqrt(T)/sigma = 0

by the Fundamental Lemma. Therefore:

    **Rho_call = dC/dr = K * T * e^(-r*T) * N(d2)**

#### 4.4.2 Derivation for European Put

Similarly:

    **Rho_put = dP/dr = -K * T * e^(-r*T) * N(-d2)**

**Verification**: Rho_call - Rho_put = K*T*e^(-r*T)*[N(d2) + N(-d2)] = K*T*e^(-r*T). From put-call parity, d(C-P)/dr = K*T*e^(-r*T). Confirmed.

#### 4.4.3 Properties of Rho

- **Call rho is positive**: Higher r increases call value (reduces PV of strike payment).
- **Put rho is negative**: Higher r decreases put value.
- **Magnitude**: Rho is proportional to T, so it matters most for LEAPS (long-dated options). For short-dated options, rho is small.
- **Scaling**: Rho is often quoted per 1% change in r, i.e., Rho/100.

### 4.5 Lambda (Omega): Leverage

    Lambda = Delta * S / V

This measures the percentage change in option price per percentage change in underlying price. Not commonly derived as a separate Greek, but follows directly from delta.

---

## 5. Second-Order Greeks

### 5.1 Gamma: d^2V/dS^2

#### 5.1.1 Derivation

Gamma = dDelta/dS. For a call:

    Delta_call = e^(-q*T) * N(d1)

Differentiate with respect to S:

    Gamma = e^(-q*T) * n(d1) * (dd1/dS) = e^(-q*T) * n(d1) * 1/(S * sigma * sqrt(T))

Therefore:

    **Gamma = e^(-q*T) * n(d1) / (S * sigma * sqrt(T))**

For q = 0:

    Gamma = n(d1) / (S * sigma * sqrt(T))

#### 5.1.2 Gamma is the Same for Calls and Puts

From put-call parity: Delta_call - Delta_put = e^(-q*T), which is constant with respect to S. Therefore dDelta_call/dS = dDelta_put/dS, i.e., Gamma_call = Gamma_put.

#### 5.1.3 Properties of Gamma

- **Always positive**: n(d1) > 0, so Gamma > 0 for both calls and puts. Options are always convex in S.
- **ATM maximum**: Gamma is maximized near d1 = 0 (ATM), where n(d1) = n(0) = 1/sqrt(2*pi) is maximal. More precisely, Gamma is maximized when d1 = 0, i.e., when S = K*exp(-(r-q-sigma^2/2)*T).
- **Bell-curve shape**: As a function of S, Gamma has a bell-shaped profile centered near ATM. This follows because n(d1) is a Gaussian in ln(S), and the 1/S factor slightly skews the peak.
- **Time behavior**: Gamma ~ n(d1)/(S*sigma*sqrt(T)). For ATM options (d1 ~ 0), Gamma ~ 1/(S*sigma*sqrt(T)*sqrt(2*pi)), which grows as 1/sqrt(T) as T -> 0. ATM gamma explodes near expiration.
- **OTM/ITM options**: For deep OTM/ITM, d1 is large in magnitude, so n(d1) ~ 0, giving Gamma ~ 0. Far from ATM, the option behaves nearly linearly in S.

#### 5.1.4 Dollar Gamma and GEX

**Dollar Gamma**: Measures the dollar change in delta for a 1% move in S:

    Dollar Gamma = (1/2) * Gamma * S^2 * 0.01^2 = Gamma * S^2 / 20000  [for P&L of 1% move]

More commonly quoted as:

    Dollar Gamma per 1% move = Gamma * S^2 / 100

**GEX (Gamma Exposure)**: For a position with open interest OI:

    GEX = Gamma * OI * 100 * S^2 / 100 = Gamma * OI * S^2

The factor of 100 accounts for the standard option multiplier (1 contract = 100 shares). In practice:

    GEX_per_contract = Gamma * S^2 * 100

    Total GEX = sum over all strikes of [Gamma_i * OI_i * 100 * S^2]

This measures the total dollar delta change across all dealer positions per 1% move in the underlying.

**Derivation of the "per 1% move" form**: If S moves by dS = 0.01*S (a 1% move), the change in delta is:

    d(Delta) = Gamma * dS = Gamma * 0.01 * S

The dollar value of this delta change (in terms of 100-share contracts):

    Dollar Delta Change = Gamma * 0.01 * S * 100 * S = Gamma * S^2

### 5.2 Vanna: d^2V/(dS * dsigma)

#### 5.2.1 Derivation (Method 1: dDelta/dsigma)

    Vanna = d(Delta)/dsigma = d[e^(-q*T) * N(d1)] / dsigma = e^(-q*T) * n(d1) * dd1/dsigma

We showed dd1/dsigma = -d2/sigma. Therefore:

    **Vanna = -e^(-q*T) * n(d1) * d2 / sigma**

For q = 0:

    Vanna = -n(d1) * d2 / sigma

#### 5.2.2 Derivation (Method 2: dVega/dS)

By Schwarz's theorem (equality of mixed partial derivatives), since V is smooth:

    d^2V/(dS*dsigma) = d^2V/(dsigma*dS)

So Vanna = dVega/dS. Let's verify:

    Vega = S * e^(-q*T) * n(d1) * sqrt(T)

    dVega/dS = e^(-q*T) * n(d1) * sqrt(T)
             + S * e^(-q*T) * n'(d1) * dd1/dS * sqrt(T)

Since n'(d1) = -d1 * n(d1) and dd1/dS = 1/(S*sigma*sqrt(T)):

    dVega/dS = e^(-q*T)*n(d1)*sqrt(T) + S*e^(-q*T)*(-d1*n(d1))*(1/(S*sigma*sqrt(T)))*sqrt(T)
             = e^(-q*T)*n(d1)*sqrt(T) - e^(-q*T)*n(d1)*d1/sigma
             = e^(-q*T)*n(d1)*[sqrt(T) - d1/sigma]
             = e^(-q*T)*n(d1)*(-d2/sigma)         [since -d2/sigma = sqrt(T) - d1/sigma]
             = -e^(-q*T)*n(d1)*d2/sigma

This confirms the result: Vanna = dDelta/dsigma = dVega/dS. QED.

#### 5.2.3 Alternative Form

Using the Fundamental Lemma (A = S*e^(-q*T)*n(d1)):

    Vanna = -A * d2 / (S * sigma) = -(Vega/S) * (d2/sqrt(T))

Or equivalently:

    Vanna = (Vega/S) * [1 - d1/(sigma*sqrt(T))]

Since Vega = S*e^(-q*T)*n(d1)*sqrt(T), we have Vega/S = e^(-q*T)*n(d1)*sqrt(T), so:

    Vanna = e^(-q*T)*n(d1)*sqrt(T)*[1 - d1/(sigma*sqrt(T))]/1
                ... wait, let's be precise:
    Vanna = -e^(-q*T)*n(d1)*d2/sigma

Check: [1 - d1/(sigma*sqrt(T))] = [sigma*sqrt(T) - d1]/(sigma*sqrt(T)) = -d2/(sigma*sqrt(T))

So Vega/S * [1 - d1/(sigma*sqrt(T))] = e^(-q*T)*n(d1)*sqrt(T) * [-d2/(sigma*sqrt(T))]
= -e^(-q*T)*n(d1)*d2/sigma = Vanna. Confirmed.

#### 5.2.4 Vanna is the Same for Calls and Puts

Since Vega_call = Vega_put and Vanna = dVega/dS, it follows immediately that Vanna_call = Vanna_put.

Alternatively: Delta_call - Delta_put = e^(-q*T) (constant in sigma), so dDelta_call/dsigma = dDelta_put/dsigma.

#### 5.2.5 Sign Analysis of Vanna

    Vanna = -e^(-q*T) * n(d1) * d2 / sigma

Since e^(-q*T), n(d1), and sigma are all positive, the sign of Vanna is determined by -d2:

- **Vanna > 0 when d2 < 0**: This occurs when ln(S/K) + (r - q - sigma^2/2)*T < 0, i.e., the option is OTM (for a call, S < K*exp(-(r-q-sigma^2/2)*T)).
- **Vanna < 0 when d2 > 0**: This occurs for ITM options.
- **Vanna = 0 when d2 = 0**: This is at a specific moneyness level.

**Practical interpretation**:
- **OTM calls (d2 < 0, Vanna > 0)**: When implied volatility increases, the delta of OTM calls increases. Conversely, when IV drops, OTM call deltas shrink.
- **ITM calls (d2 > 0, Vanna < 0)**: When IV increases, ITM call delta decreases toward 0.5. When IV drops, ITM call delta increases toward 1.
- **OTM puts**: Since Delta_put = Delta_call - e^(-q*T), Vanna_put = Vanna_call (same formula). For OTM puts (where d2 > 0 from the call perspective with same strike -- but the put is OTM when S < K, meaning d2 can be either sign). More precisely: for puts that are OTM, S < K, and d2 is typically negative, so Vanna > 0. When IV increases, the put delta magnitude |Delta_put| increases (delta becomes more negative).

**Vanna flows**: When implied volatility drops, the deltas of OTM options shrink. If dealers are long OTM options, their delta hedges (short stock for calls, long stock for puts) become oversized, requiring them to unwind -- buying back stock (for call hedges) or selling stock (for put hedges). This creates directional flow from vanna.

### 5.3 Volga (Vomma): d^2V/dsigma^2

#### 5.3.1 Derivation

Volga = dVega/dsigma. Starting from:

    Vega = S * e^(-q*T) * n(d1) * sqrt(T)

Differentiate with respect to sigma:

    dVega/dsigma = S * e^(-q*T) * sqrt(T) * n'(d1) * dd1/dsigma

Since n'(d1) = -d1*n(d1) and dd1/dsigma = -d2/sigma:

    dVega/dsigma = S * e^(-q*T) * sqrt(T) * (-d1 * n(d1)) * (-d2/sigma)
                 = S * e^(-q*T) * sqrt(T) * n(d1) * d1 * d2 / sigma

Therefore:

    **Volga = Vega * d1 * d2 / sigma**

Or equivalently:

    Volga = S * e^(-q*T) * n(d1) * sqrt(T) * d1 * d2 / sigma

For q = 0:

    Volga = S * n(d1) * sqrt(T) * d1 * d2 / sigma

#### 5.3.2 Volga is the Same for Calls and Puts

Since Vega is the same for calls and puts, Volga = dVega/dsigma is also the same.

#### 5.3.3 Sign Analysis

    Volga = Vega * d1 * d2 / sigma

Since Vega > 0 and sigma > 0, the sign depends on d1*d2:

- **Volga > 0 when d1*d2 > 0**: This occurs when d1 and d2 have the same sign, i.e., both positive (deep ITM) or both negative (deep OTM). Since d1 = d2 + sigma*sqrt(T), and sigma*sqrt(T) > 0, we need d2 > 0 (giving d1 > 0) or d1 < 0 (giving d2 < 0).
- **Volga < 0 when d1*d2 < 0**: This occurs in a band around ATM where d2 < 0 < d1, i.e., when |ln(S/K) + (r-q)*T| < sigma^2*T/2.
- **Volga = 0 when d1 = 0 or d2 = 0**: At these specific moneyness levels.

**Interpretation**: Volga measures the convexity of option price with respect to volatility.
- **Long volga (OTM wings)**: Benefits from vol-of-vol. If you are long OTM options, you benefit from large volatility moves in either direction.
- **This is the connection to the volatility smile**: The smile arises because OTM options have positive volga, and the market prices in the value of this vol-of-vol exposure.

### 5.4 Charm (Delta Decay): d^2V/(dS*dt) = -d^2V/(dS*dT)

#### 5.4.1 Derivation

Charm = dDelta/dt = -dDelta/dT. For a call:

    Delta_call = e^(-q*T) * N(d1)

Differentiate with respect to T:

    dDelta/dT = q * e^(-q*T) * N(d1) + e^(-q*T) * n(d1) * dd1/dT

We need dd1/dT. From d1 = [ln(S/K) + (r-q+sigma^2/2)*T] / (sigma*sqrt(T)):

    dd1/dT = (r-q+sigma^2/2)/(sigma*sqrt(T)) - [ln(S/K) + (r-q+sigma^2/2)*T]/(2*T*sigma*sqrt(T))
           = (r-q+sigma^2/2)/(sigma*sqrt(T)) - d1/(2T)

Using d1 = [ln(S/K) + (r-q+sigma^2/2)*T]/(sigma*sqrt(T)), we can write:

    dd1/dT = [(r-q+sigma^2/2)*2T - sigma*sqrt(T)*d1] / (2T*sigma*sqrt(T))

This is complex. An alternative cleaner approach uses the relationship:

    d1/(2T) = [ln(S/K) + (r-q+sigma^2/2)*T] / (2T*sigma*sqrt(T))

Let's compute dd1/dT directly:

    dd1/dT = d/dT { [ln(S/K) + (r-q+sigma^2/2)*T] / (sigma*sqrt(T)) }
           = { (r-q+sigma^2/2) * sigma*sqrt(T) - [ln(S/K) + (r-q+sigma^2/2)*T] * sigma/(2*sqrt(T)) } / (sigma^2 * T)
           = { (r-q+sigma^2/2)*sqrt(T) - [ln(S/K) + (r-q+sigma^2/2)*T]/(2*sqrt(T)) } / (sigma*T)

Multiply numerator and denominator by 2*sqrt(T):

    = { 2*(r-q+sigma^2/2)*T - [ln(S/K) + (r-q+sigma^2/2)*T] } / (2*sigma*T*sqrt(T))
    = { (r-q+sigma^2/2)*T - ln(S/K) } / (2*sigma*T*sqrt(T))

Note that (r-q+sigma^2/2)*T - ln(S/K) = sigma*sqrt(T)*d1 - 2*ln(S/K) ... Hmm, let's try another approach.

Write d2 = d1 - sigma*sqrt(T). Then:

    2*(r-q)*T - d2*sigma*sqrt(T) = 2*(r-q)*T - (d1 - sigma*sqrt(T))*sigma*sqrt(T)
    = 2*(r-q)*T - d1*sigma*sqrt(T) + sigma^2*T

Now d1*sigma*sqrt(T) = ln(S/K) + (r-q+sigma^2/2)*T, so:

    = 2*(r-q)*T - ln(S/K) - (r-q+sigma^2/2)*T + sigma^2*T
    = 2*(r-q)*T - ln(S/K) - (r-q)*T - sigma^2*T/2 + sigma^2*T
    = (r-q)*T - ln(S/K) + sigma^2*T/2
    = (r-q+sigma^2/2)*T - ln(S/K)

This confirms that (r-q+sigma^2/2)*T - ln(S/K) = 2*(r-q)*T - d2*sigma*sqrt(T).

Therefore:

    dd1/dT = [2*(r-q)*T - d2*sigma*sqrt(T)] / (2*sigma*T*sqrt(T))

So Charm for a call:

    Charm_call = -dDelta_call/dT = -q*e^(-q*T)*N(d1) - e^(-q*T)*n(d1)*dd1/dT

    **Charm_call = -q*e^(-q*T)*N(d1) - e^(-q*T)*n(d1) * [2*(r-q)*T - d2*sigma*sqrt(T)] / (2*T*sigma*sqrt(T))**

For q = 0:

    Charm_call = -n(d1) * [2*r*T - d2*sigma*sqrt(T)] / (2*T*sigma*sqrt(T))

#### 5.4.2 Properties of Charm

- **Sign**: Charm can be positive or negative depending on moneyness and time to expiration.
- **Near expiry**: As T -> 0, charm becomes very large in magnitude, causing rapid delta changes. This is the source of "OpEx dynamics" -- the rapid re-hedging activity near option expiration.
- **Interpretation**: Charm tells you how much your delta hedge needs to be adjusted purely due to time passing (not due to price or vol moves). A portfolio with large charm exposure requires frequent delta rebalancing.
- **Charm-driven flows**: Near expiration, ITM call charm is negative (delta increases toward 1), while OTM call charm is positive (delta decreases toward 0). Dealers must adjust hedges accordingly, creating buying/selling pressure.

### 5.5 Veta: d^2V/(dsigma * dt)

Veta = dVega/dt = -dVega/dT. Starting from Vega = S*e^(-q*T)*n(d1)*sqrt(T):

    dVega/dT = S * [-q*e^(-q*T)*n(d1)*sqrt(T) + e^(-q*T)*n'(d1)*(dd1/dT)*sqrt(T) + e^(-q*T)*n(d1)/(2*sqrt(T))]

This yields:

    **Veta = -dVega/dT = S*e^(-q*T)*n(d1)*sqrt(T) * [q + d1*{2(r-q)*T - d2*sigma*sqrt(T)}/(2*T*sigma*sqrt(T)) - 1/(2T)]**

A simpler form (for q = 0):

    Veta = -S*n(d1)*sqrt(T) * [r*d1/(sigma*sqrt(T)) - (1 + d1*d2)/(2T)]

Veta describes how vega changes with time -- the "term structure decay" of vega.

---

## 6. Third-Order Greeks

### 6.1 Speed: d^3V/dS^3 = dGamma/dS

#### 6.1.1 Derivation

Starting from:

    Gamma = e^(-q*T) * n(d1) / (S * sigma * sqrt(T))

Differentiate with respect to S:

    dGamma/dS = e^(-q*T) / (sigma*sqrt(T)) * d/dS [n(d1) / S]
              = e^(-q*T) / (sigma*sqrt(T)) * [n'(d1)*(dd1/dS)/S - n(d1)/S^2]
              = e^(-q*T) / (sigma*sqrt(T)) * [-d1*n(d1)/(S^2*sigma*sqrt(T)) - n(d1)/S^2]
              = -e^(-q*T)*n(d1) / (S^2*sigma*sqrt(T)) * [d1/(sigma*sqrt(T)) + 1]

Therefore:

    **Speed = -Gamma/S * [1 + d1/(sigma*sqrt(T))]**

Or equivalently:

    Speed = -e^(-q*T)*n(d1) / (S^2 * sigma^2 * T) * [d1 + sigma*sqrt(T)]
          = -e^(-q*T)*n(d1) / (S^2 * sigma^2 * T) * [d1 + sigma*sqrt(T)]

Note that d1 + sigma*sqrt(T) = d1 + (d1 - d2) = 2*d1 - d2 ... Actually:
d1 + sigma*sqrt(T) is not simply d1 - d2 since d2 = d1 - sigma*sqrt(T), so sigma*sqrt(T) = d1 - d2, giving d1 + sigma*sqrt(T) = 2*d1 - d2.

Cleaner form:

    Speed = -Gamma * [d1/(sigma*sqrt(T)) + 1] / S

#### 6.1.2 Properties

- Speed tells how gamma changes with spot. It is important for traders with large gamma positions, as it determines how quickly gamma can flip from being helpful to harmful.
- Speed is negative when d1 > -sigma*sqrt(T) (i.e., for most practical cases), meaning gamma decreases as the underlying moves away from ATM.
- For gamma scalping, speed determines the rate at which your gamma advantage dissipates as the stock moves.

### 6.2 Zomma: d^3V/(dS^2 * dsigma) = dGamma/dsigma

#### 6.2.1 Derivation

Starting from:

    Gamma = e^(-q*T) * n(d1) / (S * sigma * sqrt(T))

Differentiate with respect to sigma:

    dGamma/dsigma = e^(-q*T) / (S*sqrt(T)) * d/dsigma [n(d1)/sigma]
                  = e^(-q*T) / (S*sqrt(T)) * [n'(d1)*(dd1/dsigma)/sigma - n(d1)/sigma^2]
                  = e^(-q*T) / (S*sqrt(T)) * [-d1*n(d1)*(-d2/sigma)/sigma - n(d1)/sigma^2]
                  = e^(-q*T)*n(d1) / (S*sigma^2*sqrt(T)) * [d1*d2 - 1]

Therefore:

    **Zomma = Gamma * (d1*d2 - 1) / sigma**

#### 6.2.2 Properties

- Zomma tells you how gamma changes when volatility changes. For traders with large gamma positions in volatile markets, zomma determines whether a vol spike will increase or decrease their gamma.
- **Sign**: Zomma > 0 when d1*d2 > 1 (deep OTM or deep ITM); Zomma < 0 when d1*d2 < 1 (near ATM).
- Near ATM where d1 ~ 0, d2 ~ -sigma*sqrt(T), we have d1*d2 ~ 0 < 1, so Zomma < 0. This means a vol increase reduces ATM gamma (gamma peak broadens but becomes lower).

### 6.3 Color (Gamma Decay): d^3V/(dS^2 * dt) = dGamma/dt = -dGamma/dT

#### 6.3.1 Derivation

Starting from:

    Gamma = e^(-q*T) * n(d1) / (S * sigma * sqrt(T))

Differentiate with respect to T:

    dGamma/dT = e^(-q*T)/(S*sigma) * d/dT [n(d1)/sqrt(T)]
              + (-q)*e^(-q*T)*n(d1)/(S*sigma*sqrt(T))

    d/dT[n(d1)/sqrt(T)] = n'(d1)*(dd1/dT)/sqrt(T) - n(d1)/(2*T^(3/2))
                         = -d1*n(d1)*(dd1/dT)/sqrt(T) - n(d1)/(2*T^(3/2))

This becomes involved. The result is:

    **Color = -dGamma/dT = -(e^(-q*T)*n(d1))/(2*S*sigma*T*sqrt(T)) * [2*q*T + 1 + d1 * (2*(r-q)*T - d2*sigma*sqrt(T))/(sigma*sqrt(T))]**

For q = 0:

    Color = -(n(d1))/(2*S*sigma*T*sqrt(T)) * [1 + d1*(2*r*T - d2*sigma*sqrt(T))/(sigma*sqrt(T))]

#### 6.3.2 Properties

- **Gamma explosion**: As T -> 0 for ATM options, gamma concentrates sharply at the strike. Color captures this rate of concentration.
- **Practical significance**: Near expiry, gamma at the strike grows rapidly while gamma away from the strike collapses. Color quantifies this effect, which drives the rapid delta changes (and therefore hedging flows) observed on expiration days.

### 6.4 Ultima: d^3V/dsigma^3

#### 6.4.1 Derivation

Ultima = dVolga/dsigma. Starting from:

    Volga = Vega * d1 * d2 / sigma

Differentiate with respect to sigma:

    dVolga/dsigma = (dVega/dsigma) * d1*d2/sigma + Vega * d/dsigma[d1*d2/sigma]

The first term: dVega/dsigma = Volga = Vega*d1*d2/sigma. So:

    First term = Vega * (d1*d2)^2 / sigma^2

For the second term:

    d/dsigma[d1*d2/sigma] = [(dd1/dsigma)*d2 + d1*(dd2/dsigma)]/sigma - d1*d2/sigma^2
                           = [(-d2/sigma)*d2 + d1*(-d1/sigma)]/sigma - d1*d2/sigma^2
                           = [-d2^2 - d1^2]/(sigma^2) - d1*d2/sigma^2
                           = -(d1^2 + d1*d2 + d2^2)/sigma^2

So:

    Second term = -Vega * (d1^2 + d1*d2 + d2^2) / sigma^2

Combining:

    Ultima = Vega/sigma^2 * [(d1*d2)^2 - d1^2 - d1*d2 - d2^2]
           = Vega/sigma^2 * [d1^2*d2^2 - d1^2 - d1*d2 - d2^2]

Factoring:

    **Ultima = -(Vega/sigma^2) * [d1^2 + d2^2 + d1*d2 - d1^2*d2^2]**

Or equivalently:

    Ultima = -(Vega/sigma^2) * [d1*d2*(1 - d1*d2) + d1^2 + d2^2]

This can also be written as:

    Ultima = -Volga/sigma * [d1*d2 - d1*d2*(d1*d2 - 1) ... ]  [various equivalent forms exist]

#### 6.4.2 Properties

- Ultima is the third-order sensitivity to volatility and is extremely rarely used in practice.
- It becomes relevant only for very large portfolios with significant volga positions in markets with rapidly changing vol-of-vol.

---

## 7. The Theta-Gamma Relationship

### 7.1 Derivation from the BSM PDE

The Black-Scholes PDE (with dividends) is:

    dV/dt + (1/2)*sigma^2*S^2*(d^2V/dS^2) + (r-q)*S*(dV/dS) - r*V = 0

In terms of Greeks:

    Theta + (1/2)*sigma^2*S^2*Gamma + (r-q)*S*Delta - r*V = 0

Rearranging:

    **Theta = -(1/2)*sigma^2*S^2*Gamma - (r-q)*S*Delta + r*V**

This is an **exact identity** that holds for any option priced under BSM. It is not an approximation.

### 7.2 Economic Interpretation

Rewrite as:

    Theta + (1/2)*sigma^2*S^2*Gamma = r*V - (r-q)*S*Delta = r*(V - S*Delta) + q*S*Delta

For q = 0:

    Theta + (1/2)*sigma^2*S^2*Gamma = r*(V - S*Delta)

The right side is r times the cash position in the delta-hedged portfolio (V - Delta*S). If you hold one option (value V) and are short Delta shares (value -Delta*S), the net cash position is (V - Delta*S), which earns interest at rate r.

**Key insight**: Theta pays for gamma. You cannot have free gamma exposure. If your position has positive gamma (beneficial convexity), you must pay for it through negative theta (time decay).

### 7.3 ATM Approximation

For ATM options (with q = 0), Delta ~ 0.5 and V is relatively small compared to S:

    V - S*Delta ~ V - 0.5*S

For a call, V = S*N(d1) - K*e^(-r*T)*N(d2). At the money (S ~ K):

    V ~ S*[N(d1) - e^(-r*T)*N(d2)]

For short-dated ATM options, this is approximately sigma*S*sqrt(T)/(sqrt(2*pi)), which is small. Therefore:

    r*(V - S*Delta) is small

And the dominant relationship is:

    **Theta ~ -(1/2)*sigma^2*S^2*Gamma**    [ATM approximation]

This is the simplified "theta pays for gamma" rule.

### 7.4 P&L of a Delta-Hedged Option

Consider holding one option and continuously delta-hedging (rebalancing to maintain Delta*S shares short). Over a small time interval dt:

**Option P&L** (from Taylor expansion):

    dV = Delta*dS + (1/2)*Gamma*(dS)^2 + Theta*dt + ...

**Hedge P&L**:

    -Delta * dS    (from the short Delta*S shares)

**Net P&L**:

    dP&L = dV - Delta*dS = Theta*dt + (1/2)*Gamma*(dS)^2

Substituting (dS)^2 = sigma_realized^2 * S^2 * dt (the realized quadratic variation):

    dP&L = Theta*dt + (1/2)*Gamma*S^2*sigma_realized^2*dt

Now using the BSM relationship Theta = -(1/2)*sigma_implied^2*S^2*Gamma - r*(V - S*Delta):

    dP&L = [-(1/2)*sigma_implied^2*S^2*Gamma]*dt + (1/2)*Gamma*S^2*sigma_realized^2*dt - r*(V-S*Delta)*dt

    **dP&L = (1/2)*Gamma*S^2*(sigma_realized^2 - sigma_implied^2)*dt - r*(V - S*Delta)*dt**

Ignoring the financing term (or for short time horizons):

    **dP&L ~ (1/2)*Gamma*S^2*(sigma_realized^2 - sigma_implied^2)*dt**

### 7.5 The Fundamental Equation of Options Market Making

This is the core result:

    **Delta-hedged P&L = (1/2) * Gamma * S^2 * (sigma_realized^2 - sigma_implied^2) * dt**

**Implications**:

1. **If realized vol > implied vol**: A long gamma position profits. Gamma scalping works -- the profits from rebalancing exceed the time decay paid.

2. **If realized vol < implied vol**: A short gamma position profits (premium selling). The theta collected exceeds the losses from gamma.

3. **The P&L is path-dependent**: Even though the total P&L over the life of the option depends on cumulative realized vol vs. implied vol, the path of S affects how gamma varies, weighting different periods differently.

4. **Gamma weighting**: Gamma is largest ATM and decays away from ATM. So the realized vol in the region near the strike matters most.

5. **Over the full life of the option (held to expiry)**: Cumulative P&L = integral from 0 to T of (1/2)*Gamma*S^2*(sigma_realized^2 - sigma_implied^2)*dt. If sigma_realized^2 > sigma_implied^2 on average (weighted by Gamma*S^2), the long gamma position profits.

### 7.6 Variance Swap Connection

The integral of (1/2)*Gamma*S^2*dt over the life of the option is closely related to the variance swap. In fact, a portfolio of options across all strikes (with weights proportional to 1/K^2) replicates a variance swap, which pays realized variance minus fixed variance. This is the theoretical basis for the VIX calculation.

---

## 8. Greeks for Multi-Leg Strategies

Greeks are additive across positions. For a portfolio of n option positions with quantities w_i:

    Greek_portfolio = sum_{i=1}^{n} w_i * Greek_i

### 8.1 Vertical Spreads

#### Bull Call Spread: Long C(K1) + Short C(K2), where K1 < K2

- **Delta**: N(d1(K1)) - N(d1(K2)) > 0. Always positive but less than N(d1(K1)).
- **Gamma**: Gamma(K1) - Gamma(K2). Positive when S < (K1+K2)/2, negative when S > (K1+K2)/2 (approximately). The net gamma switches sign near the midpoint of the strikes.
- **Vega**: Vega(K1) - Vega(K2). Can be positive or negative depending on where S is relative to the strikes.
- **Theta**: Theta(K1) - Theta(K2). Generally positive (net time decay earned) when the position is profitable.

#### Bear Put Spread: Long P(K2) + Short P(K1), where K1 < K2

Mirror image of the bull call spread.

### 8.2 Straddle: Long C(K) + Long P(K)

- **Delta**: N(d1) + [N(d1) - 1] = 2*N(d1) - 1. Near zero for ATM straddles.
- **Gamma**: 2 * Gamma(K). Always positive and maximized ATM.
- **Vega**: 2 * Vega(K). Always positive -- straddles are pure long volatility positions.
- **Theta**: 2 * Theta(K). Always negative (for ATM) -- the cost of being long gamma and vega.

### 8.3 Strangle: Long C(K2) + Long P(K1), where K1 < K2

- **Delta**: N(d1(K2)) - N(-d1(K1)) = N(d1(K2)) + N(d1(K1)) - 1. Near zero if strikes are equidistant from ATM.
- **Gamma**: Gamma(K1) + Gamma(K2). Positive but less than a straddle (since both options are OTM).
- **Vega**: Vega(K1) + Vega(K2). Positive.
- **Theta**: Negative.

### 8.4 Iron Condor: Short P(K1) + Long P(K2) + Long C(K3) + Short C(K4)
where K1 < K2 < K3 < K4

- **Delta**: Near zero at center (between K2 and K3).
- **Gamma**: Negative near center (short the ATM gamma through the inner strikes). This is because you are net short options at strikes closer to ATM (K2, K3) and net long at strikes further away (K1, K4, which have lower gamma).

    Gamma_IC = -Gamma(K1) + Gamma(K2) + Gamma(K3) - Gamma(K4) ... Actually more precisely:
    The short put spread (short K1 put, long K2 put) has negative gamma near the put strikes, and the short call spread (short K4 call, long K3 call) has negative gamma near the call strikes. The combined effect is negative gamma between the short strikes.

- **Vega**: Negative (net short volatility). The iron condor profits from declining IV.
- **Theta**: Positive (time decay is your friend). This is the core trade: collect theta, pay for it with gamma risk.
- **Key relationship**: The iron condor exemplifies Theta = -(1/2)*sigma^2*S^2*Gamma. Since theta > 0, gamma must be < 0 (ignoring the r*(V-S*Delta) term).

### 8.5 Calendar Spread: Long C(K, T2) + Short C(K, T1), where T2 > T1

- **Delta**: Delta(T2) - Delta(T1). Near zero for ATM calendars.
- **Gamma**: Gamma(T2) - Gamma(T1). Since Gamma ~ 1/(sigma*sqrt(T)), Gamma(T1) > Gamma(T2) for ATM options. So **net gamma is negative** -- you are short the near-term gamma.
- **Vega**: Vega(T2) - Vega(T1). Since Vega ~ S*sqrt(T)*n(d1), Vega(T2) > Vega(T1). So **net vega is positive**.
- **Theta**: Theta(T2) - Theta(T1). Since ATM theta ~ -S*sigma/(2*sqrt(T)), |Theta(T1)| > |Theta(T2)|, so **net theta is positive** (you collect more decay from the short leg).

**The calendar spread paradox**: It is simultaneously short gamma and long vega, which seems contradictory since the theta-gamma relationship says theta pays for gamma. The resolution: the calendar spread profits from the term structure -- the near-term option decays faster (theta) while the far-term option provides vega exposure. The position benefits from stable realized vol (short gamma) but increasing implied vol of the back month (long vega).

### 8.6 Ratio Spread: Long 1x C(K1) + Short nx C(K2), n > 1, K2 > K1

- **Delta**: N(d1(K1)) - n*N(d1(K2)). Can be positive, negative, or zero.
- **Gamma**: Gamma(K1) - n*Gamma(K2). **Gamma flips sign** at the strike where the weighted gammas balance. Below K2, gamma is positive (the long K1 call dominates); above K2, gamma becomes negative (the n short K2 calls dominate).
- **The zero-gamma point** occurs approximately where n*n(d1(K2))/(K2*sigma*sqrt(T)) = n(d1(K1))/(K1*sigma*sqrt(T)).

### 8.7 Butterfly: Long C(K1) + Short 2*C(K2) + Long C(K3), where K1 < K2 < K3

where K2 = (K1 + K3)/2 (equidistant strikes).

- **Delta**: N(d1(K1)) - 2*N(d1(K2)) + N(d1(K3)). Near zero at K2.
- **Gamma**: Gamma(K1) - 2*Gamma(K2) + Gamma(K3). **Peaked negative gamma at K2** (since Gamma(K2) is the largest). The butterfly is short gamma at the center and long gamma at the wings.
- **Theta**: Positive at center (collecting decay from the two short options).
- **The butterfly is essentially a bet on realized vol being low**: Maximum profit if S stays at K2 through expiration.

---

## 9. Greeks Under Different Models

### 9.1 The Heston Stochastic Volatility Model

#### 9.1.1 Model Specification

Under the Heston model, the asset price and its instantaneous variance follow:

    dS = mu*S*dt + sqrt(v)*S*dW_1
    dv = kappa*(theta_v - v)*dt + xi*sqrt(v)*dW_2

where:
- v(t) is the instantaneous variance (sigma^2)
- kappa is the mean-reversion speed of variance
- theta_v is the long-run variance level
- xi is the "vol of vol"
- dW_1 and dW_2 are correlated Brownian motions with correlation rho_corr
- The Feller condition 2*kappa*theta_v > xi^2 ensures v > 0

#### 9.1.2 Option Pricing

The Heston model admits a semi-analytical solution via characteristic functions:

    C = S*e^(-q*T)*P_1 - K*e^(-r*T)*P_2

where P_1 and P_2 are computed as:

    P_j = 1/2 + (1/pi) * integral from 0 to infinity of Re[exp(-i*phi*ln(K)) * f_j(phi)] / (i*phi) d_phi

and f_j are the characteristic functions of ln(S(T)) under the respective measures. These characteristic functions have known closed-form expressions involving complex exponentials and hyperbolic functions.

#### 9.1.3 Greeks in the Heston Model

There are no simple closed-form Greeks analogous to BSM. Instead:

- **Delta**: Computed by differentiating the characteristic function integrals with respect to S.
- **Gamma**: Second derivative of the integral representation.
- **Vega**: In the Heston model, "vega" can refer to sensitivity to the current instantaneous vol sqrt(v), or to the long-run vol sqrt(theta_v), or to xi (vol of vol). Each requires differentiating the characteristic function.

A key advantage of the Heston model over BSM: it produces a volatility smile/skew naturally, without needing different implied vols for different strikes. The Greeks automatically account for the smile dynamics.

### 9.2 Local Volatility (Dupire)

#### 9.2.1 The Dupire Formula

In the local volatility framework, sigma is a deterministic function of S and t: sigma = sigma_LV(S, t).

The Dupire equation relates local vol to the implied vol surface:

    sigma_LV^2(K, T) = [dC/dT + (r-q)*K*(dC/dK) + q*C] / [(1/2)*K^2*(d^2C/dK^2)]

where the derivatives are of the observed call prices with respect to strike and maturity.

#### 9.2.2 Greeks Under Local Vol

The BSM PDE generalizes to:

    dV/dt + (1/2)*sigma_LV(S,t)^2 * S^2 * d^2V/dS^2 + (r-q)*S*dV/dS - r*V = 0

Greeks are computed numerically (typically via finite differences or Monte Carlo), since sigma_LV depends on S. The key difference from BSM: delta and gamma implicitly account for the fact that vol changes as S changes.

### 9.3 Model-Free Greek Bounds

Certain inequalities hold regardless of the model:

- **Delta bounds**: 0 <= Delta_call <= e^(-q*T) and -e^(-q*T) <= Delta_put <= 0 (from no-arbitrage).
- **Gamma is non-negative** for convex payoffs (calls, puts) under any arbitrage-free model.
- **Put-call parity Greeks**: Delta_call - Delta_put = e^(-q*T), Gamma_call = Gamma_put, Vega_call = Vega_put. These hold model-free.
- **Vega non-negativity**: For European calls and puts, vega >= 0 under any model where the option price is a convex function of volatility. (This is not universally true for all models but holds under mild regularity conditions.)

### 9.4 Sticky Strike vs. Sticky Delta and Impact on Greeks

The BSM model with constant sigma is "model-free" about what happens to vol when S moves. In practice, the implied vol surface is not flat, and two common assumptions are:

#### 9.4.1 Sticky Strike

When S changes, the implied volatility of an option at a given **absolute strike K** remains constant:

    sigma_implied(K) does not change when S changes

**Impact on Greeks**: Under sticky strike, delta = BSM_delta (no adjustment needed). The vol smile is fixed, and delta-hedging uses the BSM delta computed at the option's own implied vol. This assumption tends to hold in risk-off/high-volatility regimes.

#### 9.4.2 Sticky Delta (Sticky Moneyness)

When S changes, the implied volatility at a given **moneyness level** K/S (or delta level) remains constant:

    sigma_implied depends only on K/S (or equivalently, on delta)

**Impact on Greeks**: Under sticky delta, the BSM delta must be adjusted:

    Delta_adjusted = Delta_BSM + Vega * (dsigma/dS)

where dsigma/dS is the rate at which implied vol changes when S moves. For a negatively sloped skew (typical for equities):

    dsigma/dS < 0 (vol increases when S drops)

So Delta_adjusted < Delta_BSM for calls (and |Delta_adjusted| > |Delta_BSM| for puts). This means you need to hedge with fewer shares than BSM suggests (for calls).

The practical implication: sticky delta hedging requires "smile adjustment" to delta:

    Delta_smile = Delta_BSM + Vega_BSM * (dsigma_implied / dS)

This adjustment can be significant for skewed markets and is essential for accurate hedging of index options.

#### 9.4.3 Reality

Neither assumption is fully correct. Empirical evidence suggests:
- Short-dated index options: closer to sticky strike during risk-off, sticky delta during trending markets
- Long-dated options (> 5 years): closer to sticky delta
- Single stocks: behavior varies

---

## 10. Summary Formula Sheet

### Notation
- S: spot price, K: strike, T: time to expiry, r: risk-free rate, q: dividend yield, sigma: volatility
- d1 = [ln(S/K) + (r - q + sigma^2/2)*T] / (sigma*sqrt(T))
- d2 = d1 - sigma*sqrt(T)
- n(x) = (1/sqrt(2*pi))*exp(-x^2/2) [standard normal PDF]
- N(x) = integral of n(u) from -infinity to x [standard normal CDF]
- Fundamental Lemma: S*e^(-q*T)*n(d1) = K*e^(-r*T)*n(d2)

### Option Prices

| | Call | Put |
|---|------|-----|
| Price | S*e^(-qT)*N(d1) - K*e^(-rT)*N(d2) | K*e^(-rT)*N(-d2) - S*e^(-qT)*N(-d1) |

### First-Order Greeks

| Greek | Definition | Call | Put |
|-------|-----------|------|-----|
| Delta | dV/dS | e^(-qT)*N(d1) | -e^(-qT)*N(-d1) |
| Vega | dV/dsigma | S*e^(-qT)*n(d1)*sqrt(T) | same |
| Theta | dV/dt | -Se^(-qT)*n(d1)*sigma/(2sqrt(T)) - rKe^(-rT)*N(d2) + qSe^(-qT)*N(d1) | -Se^(-qT)*n(d1)*sigma/(2sqrt(T)) + rKe^(-rT)*N(-d2) - qSe^(-qT)*N(-d1) |
| Rho | dV/dr | KTe^(-rT)*N(d2) | -KTe^(-rT)*N(-d2) |

### Second-Order Greeks

| Greek | Definition | Formula (same for calls and puts unless noted) |
|-------|-----------|------------------------------------------------|
| Gamma | d^2V/dS^2 | e^(-qT)*n(d1) / (S*sigma*sqrt(T)) |
| Vanna | d^2V/(dS*dsigma) | -e^(-qT)*n(d1)*d2/sigma |
| Volga | d^2V/dsigma^2 | Vega*d1*d2/sigma |
| Charm | -d^2V/(dS*dT) | -qe^(-qT)*N(d1) - e^(-qT)*n(d1)*[2(r-q)T - d2*sigma*sqrt(T)]/(2T*sigma*sqrt(T)) [call] |
| Veta | -d^2V/(dsigma*dT) | [complex; see Section 5.5] |

### Third-Order Greeks

| Greek | Definition | Formula |
|-------|-----------|---------|
| Speed | d^3V/dS^3 | -Gamma/S * [1 + d1/(sigma*sqrt(T))] |
| Zomma | d^3V/(dS^2*dsigma) | Gamma*(d1*d2 - 1)/sigma |
| Color | -d^3V/(dS^2*dT) | [see Section 6.3] |
| Ultima | d^3V/dsigma^3 | -(Vega/sigma^2)*[d1^2 + d2^2 + d1*d2 - d1^2*d2^2] |

### Key Identities and Relationships

1. **BSM PDE in Greeks**: Theta + (1/2)*sigma^2*S^2*Gamma + (r-q)*S*Delta - r*V = 0
2. **Theta-Gamma**: Theta = -(1/2)*sigma^2*S^2*Gamma - (r-q)*S*Delta + r*V
3. **ATM approximation**: Theta ~ -(1/2)*sigma^2*S^2*Gamma
4. **Delta-hedged P&L**: dP&L = (1/2)*Gamma*S^2*(sigma_realized^2 - sigma_implied^2)*dt
5. **Put-call parity Greeks**: Delta_C - Delta_P = e^(-qT); Gamma_C = Gamma_P; Vega_C = Vega_P; Rho_C - Rho_P = KTe^(-rT)
6. **Schwarz symmetry**: dDelta/dsigma = dVega/dS (Vanna); dGamma/dsigma = dVanna/dS (Zomma); etc.
7. **GEX**: GEX = Gamma * OI * 100 * S^2

---

## References

### Textbooks
- Hull, J.C. "Options, Futures, and Other Derivatives" -- Standard reference for BSM derivation and Greeks
- Shreve, S.E. "Stochastic Calculus for Finance II: Continuous-Time Models" -- Rigorous mathematical treatment
- Wilmott, P. "Paul Wilmott on Quantitative Finance" -- Comprehensive PDE approach to Greeks
- Taleb, N.N. "Dynamic Hedging: Managing Vanilla and Exotic Options" -- Practical Greeks and hedging
- Gatheral, J. "The Volatility Surface" -- Heston model, local vol, and smile dynamics

### Online Resources
- [Black-Scholes Model - Wikipedia](https://en.wikipedia.org/wiki/Black%E2%80%93Scholes_model)
- [Greeks (finance) - Wikipedia](https://en.wikipedia.org/wiki/Greeks_(finance))
- [Macroption: Black-Scholes Formulas](https://www.macroption.com/black-scholes-formula/)
- [Macroption: Higher Order Greeks](https://www.macroption.com/higher-order-greeks/)
- [QuantPie: Black-Scholes Greeks Derivation](https://www.quantpie.co.uk/bsm_formula/bs_summary.php)
- [Gregory Gundersen: The Greeks](https://gregorygundersen.com/blog/2023/10/08/greeks/)
- [BSIC Bocconi: Guide to Higher Order Greeks](https://bsic.it/guide-land-higher-order-greeks/)
- [Columbia University: The Black-Scholes Model (Haugh)](https://www.columbia.edu/~mh2078/FoundationsFE/BlackScholes.pdf)
- [On Derivations of Black-Scholes Greek Letters (Academic Paper)](https://files.core.ac.uk/download/pdf/234629502.pdf)
- [UT Austin: Option Greeks Slides](https://web.ma.utexas.edu/users/mcudina/m339w-slides-option-greeks.pdf)
- [FE Press: Explaining the Magic of Greeks Computations](https://www.fepress.org/wp-content/uploads/2011/03/2nd_ed-math_primer-greeks_magic.pdf)
- [Quant Next: Options Greeks and P&L Decomposition Part 1](https://quant-next.com/option-greeks-and-pl-decomposition-part-1/)
- [Quant Next: Options Greeks and P&L Decomposition Part 2](https://quant-next.com/options-greeks-and-pl-decomposition-part-2/)
- [Heston Model - Wikipedia](https://en.wikipedia.org/wiki/Heston_model)
- [Local Volatility - Wikipedia](https://en.wikipedia.org/wiki/Local_volatility)
- [Delta Quants: Sticky Strike vs Sticky Delta](http://deltaquants.com/volatility-sticky-strike-vs-sticky-delta)
- [MathFinance: Vanna-Volga and the Greeks](https://www.mathfinance.com/wp-content/uploads/2025/01/FX_Column_2020-07-VannaVolgaGreeks.pdf)
- [HyperVolatility: Vanna, Charm, Vomma, DvegaDtime](https://medium.com/hypervolatility/options-greeks-vanna-charm-vomma-dvegadtime-77d35c4db85c)
