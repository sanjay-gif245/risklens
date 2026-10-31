# Worked example: two stocks, five days, by hand

This is the reference calculation the unit tests reproduce
(`backend/tests/unit/test_hand_calculation.py`). Every number below can be
checked with a pencil. The data is deliberately tiny and has zero mean so the
arithmetic stays clean.

## Inputs

Daily log returns, in percent:

| Day | Stock A | Stock B |
|-----|--------:|--------:|
| 1   |  1      |  2      |
| 2   | -1      | -2      |
| 3   |  2      |  1      |
| 4   |  0      |  1      |
| 5   | -2      | -2      |

Weights: 60% in A, 40% in B.

## 1. Covariance (sample, divide by n - 1 = 4)

Both means are 0, so the covariance is the sum of products divided by 4.
Units below are percent squared.

- Var(A) = (1 + 1 + 4 + 0 + 4) / 4 = 10 / 4 = 2.5
- Var(B) = (4 + 4 + 1 + 1 + 4) / 4 = 14 / 4 = 3.5
- Cov(A, B) = (2 + 2 + 2 + 0 + 4) / 4 = 10 / 4 = 2.5

As decimals: 0.00025, 0.00035, 0.00025. Correlation = 2.5 / sqrt(2.5 x 3.5) = 0.845.

## 2. Portfolio volatility

Variance = w_A^2 Var(A) + w_B^2 Var(B) + 2 w_A w_B Cov(A, B)

= 0.36 x 2.5 + 0.16 x 3.5 + 2 x 0.6 x 0.4 x 2.5
= 0.90 + 0.56 + 1.20 = 2.66 (percent squared) = 0.000266

- Daily volatility = sqrt(0.000266) = 0.0163095 (1.631%)
- Annualized = 0.0163095 x sqrt(252) = 0.258905 (25.89%)

The two stocks on their own would give 0.6 x 1.581 + 0.4 x 1.871 = 1.697%.
The portfolio is lower (1.631%) because the correlation is below 1: that gap is
diversification.

## 3. Parametric VaR (normal, mean 0.0 for this data)

z at 5% = -1.644854, z at 1% = -2.326348.

- 95% 1-day VaR = 1.644854 x 0.0163095 = 0.026827 (2.683% of portfolio value)
- 99% 1-day VaR = 2.326348 x 0.0163095 = 0.037942 (3.794%)

## 4. Historical VaR and CVaR

Portfolio returns day by day, 0.6 A + 0.4 B (percent):
1.4, -1.4, 1.6, 0.4, -2.0. Sorted: -2.0, -1.4, 0.4, 1.4, 1.6.

The 5th percentile sits at position (n - 1) x 0.05 = 0.2 between the first and
second values, using linear interpolation:

-2.0 + 0.2 x (-1.4 - (-2.0)) = -2.0 + 0.12 = -1.88

- 95% 1-day historical VaR = 1.88%
- 95% CVaR = average of the returns at or below -1.88 = -2.0, so 2.0%

With only five observations this is a toy: the point is the mechanics.

## 5. Risk contributions

Covariance times weights, (S w)_i, in percent squared:

- (S w)_A = 2.5 x 0.6 + 2.5 x 0.4 = 2.5
- (S w)_B = 2.5 x 0.6 + 3.5 x 0.4 = 2.9

Marginal products w_i (S w)_i: A = 0.6 x 2.5 = 1.5, B = 0.4 x 2.9 = 1.16.
They add to 2.66, the portfolio variance. Dividing by the daily volatility
(1.63095) gives the contributions in volatility units:

| | Weight | Contribution (daily) | Share of risk |
|-|-------:|---------------------:|--------------:|
| A | 60% | 0.919709% | 56.39% |
| B | 40% | 0.711242% | 43.61% |

They sum to 1.630951%, the portfolio volatility. Annualized, the contributions
are 14.600% and 11.291%, summing to 25.891%.

## 6. Kupiec test, a second hand case

Suppose a 95% VaR model is backtested over N = 100 days and breaches x = 2
times. Expected breach probability p = 0.05, observed rate x / N = 0.02.

- ln L0 = 98 ln(0.95) + 2 ln(0.05) = -5.0268 - 5.9915 = -11.0182
- ln L1 = 98 ln(0.98) + 2 ln(0.02) = -1.9799 - 7.8240 = -9.8039
- LR = -2 (ln L0 - ln L1) = 2.4286

Against a chi-square distribution with 1 degree of freedom the p-value is
0.1191. That is above 0.05, so the model is not rejected: two breaches instead
of five is not unusual enough to call the model wrong.
