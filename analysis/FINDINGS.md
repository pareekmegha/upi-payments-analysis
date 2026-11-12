# UPI analysis: findings

Data: NPCI monthly UPI product (2019-04 to 2026-10, 91 months), P2P/P2M split (from 2020-04), and app-level volumes (2020-06 to 2026-09, 145 canonical apps, 143 brands).
Reproduce: from `analysis/`, run `01_build_master.py` through `05_stats_tests.py` in order. Charts are in `charts/`, tables in `data/`.

Units: volume in million transactions, value in Rs crore, average ticket in Rs (value x 10 / volume).

## 1. Headline findings

| # | Finding | Evidence |
|---|---|---|
| 1 | UPI volume grew 32.6x and value 22.2x from 2019-04 to 2026-10 (782 mn to 25,467 mn a month). | EDA |
| 2 | Growth is decelerating steadily, not collapsing. YoY volume growth fell from 59% (2023-04) to 23% (2026-10). Since 2022-04 the growth factor (1+YoY) has shrunk about 10% a year. | Slope -0.0091/month, 95% CI [-0.0111, -0.0071] |
| 3 | The average ticket is falling about 6% a year (Rs 1,817 in 2019-04, Rs 1,238 in 2026-10), but this is a mix effect, not shrinking payments. P2P tickets are flat (Rs 2,326 to Rs 2,328) and P2M tickets rose (Rs 514 to Rs 603). The decline comes entirely from P2M, a low-ticket segment, growing as a share of transactions. | Decomposition 2020-04 to 2026-10: -Rs 274 = mix -Rs 323 + within-segment +Rs 49 |
| 4 | The market is highly concentrated and stable at the top. PhonePe plus Google Pay hold about 80% of app volume, and the top-2 share has not moved significantly. HHI has stayed between 3,200 and 3,900 (above 2,500, the "highly concentrated" line). | Top-2 slope +0.37 pp/yr, CI [-0.32, +1.05] |
| 5 | Within the duopoly, PhonePe gained and Google Pay did not move significantly. PhonePe went from 40.7% to 46.4%. | PhonePe +0.90 pp/yr, CI [+0.09, +1.72]. Google Pay -0.54, CI [-1.29, +0.21] |
| 6 | Paytm lost share steadily, and the 2024 Paytm Payments Bank action accelerated it. Paytm's share fell from 12.5% to 7.8% around the action, against 10.7% had its 2023 trend continued. PhonePe (+1.9 pp) and Google Pay (+1.7 pp) absorbed most of it. | Diff -4.7 pp, bootstrap CI [-5.1, -4.2] |
| 7 | TPAPs went from 83% to 96.5% of app volume. Bank-owned apps are nearly gone. | Slope +3.1 pp/yr, CI [+2.3, +3.9] |
| 8 | October and February are reliably strong months. Volume per day is +3.6% in October and +2.7% in February relative to trend. Average ticket is lower in August and September (-2.4% and -1.8%). | STL, 95% CIs exclude 0 |

## 1b. Findings that are easy to miss

1. **The falling average ticket is a composition effect.** See finding 3. Reading the headline ticket alone would suggest people pay less per transaction, when per-segment tickets are flat or rising.
2. **P2M is growing faster than P2P but is still a minority of value.** P2M volume grew 73% a year vs 55% for P2P, and passed 50% of volume in 2022-08. Its value share is 30.8%, up from 15.3%.
3. **Concentration is falling in the tail even though the duopoly is flat.** The top 3 (PhonePe, Google Pay, Paytm) went from 91.6% to 85.9% of app volume. Excluding them, the HHI of the remaining apps halved (3,205 to 1,509), so the challengers are splitting up, not consolidating into a new leader.
4. **The challenger tail is almost one app.** Of the 14.1% held by everyone outside the top 3, Navi alone has 4.8% and super.money 1.7%. Navi's first report was 2023-09 and it passed 1,000 mn a month in 2026-08. The other roughly 90 brands combine for 7.6%.
5. **Brand churn is hidden by a rising count.** Reporting brands rose from 57 to 96, but 48 of 143 brands dropped out entirely. Brands that were not reporting in 2023-01 hold only 6.9% of volume now, so most new entrants stay tiny.
6. **More banks live does not mean more volume** (levels 0.98, changes 0.19). Banks live went from 148 to 758 while growth slowed.
7. **Paytm's loss did not go to the long tail.** Of its 4.7 pp loss in the six months after the 2024 action, PhonePe took 1.9 pp and Google Pay 1.7 pp, so the duopoly absorbed about 77% of it.

## 2. Correlation (on monthly changes, not levels)

Levels are almost perfectly correlated because everything trends upward together. They are misleading:

| Pair | Correlation of levels | Correlation of monthly changes |
|---|---|---|
| Volume vs value | 0.994 | 0.703 |
| Banks live vs volume | 0.984 | 0.185 |
| P2M share vs average ticket | -0.931 | -0.134 |

- Volume growth and value growth do move together (0.70), which is expected.
- Banks live and volume growth are essentially unrelated month to month (0.19). The "more banks means more volume" story is a shared trend, not a causal relationship.
- Growth in banks live correlates with changes in P2M share (0.36), top-2 share and HHI (0.32 to 0.33). All survive FDR correction, but they are descriptive, not causal.
- `top2_share` vs `hhi` changes (0.96) is mechanical, since HHI is dominated by the top-2 squared shares. Ignore it.
- Granger tests are suggestive only. Volume growth predicts later growth in banks live (p = 0.011 at lag 1), the reverse of the intuitive direction. With 8 tests run and about 75 points, I would not lean on this.
- Lead/lag correlations at the strongest lags (up to 0.40) are barely outside the noise band after picking the best of 13 lags. No usable lead/lag relationship.

## 3. Data discoveries (these affect any analysis built on this data)

1. **App `total` includes on-us volume, but the headline excludes it.** Customer-initiated + B2C + B2B equals the headline exactly (ratio 1.000) from 2020-12 to 2023, while NPCI's `total` runs 2% higher. This explains the 2% drift I flagged earlier. I added `vol_settled_mn` to `apps_clean.csv`, and all app shares here use it. It reconciles to the headline within 2% in 72 of 76 months. The remaining 4 months (2025-10 to 2025-12 and 2026-02) are about 2.5% under.
2. **Source definition change in 2020-12.** From that month NPCI credits B2C and B2B to the PSP bank. Axis Bank jumps 18x (5 mn to 92 mn) for this reason. Bank-app volumes before and after 2020-12 are not comparable on `vol_mn`.
3. **From 2025 the on-us column is a memo, not an addend.** The component-sum identity stops working, which is why I didn't impute `total` more widely.
4. **Source anomalies, flagged but not changed:** FamPay 2023-02 (1.6 mn between 12.8 and 9.5) and Bharat Pe 2025-09 (16.1 mn between 4.7 and 1.8). Also PhonePe and Google Pay `val_cr` are missing at the source for 2022-02 and 2022-03.
5. **Rename candidate for your review:** Tata Neu (ends 2025-05, 0.45 mn) and Tata Pay (starts 2025-06, 0.47 mn) look like one app renamed. I did not merge them. See `data/stats_rename_candidates.csv`. The detector's other hit is Paytm Payments Bank to Paytm, which is the split you made deliberately.

## 4. What the data cannot support

- **WhatsApp's 2024-12-31 onboarding-cap removal is not detectable.** Mean monthly growth went from 6.9% to 3.6% after, but the 95% bootstrap CI is [-8.0%, +1.8%] (n = 9 months each side). Absence of evidence, not evidence of no effect.
- **Seasonality is weak.** Seasonal strength is 0.38 for volume and 0.30 for ticket. Only 4 of 24 month effects are significant, and at a 5% threshold about 1 false positive is expected among 24. April to June CIs are very wide because 2020 COVID distorts those months. Treat Oct and Feb as likely, and the rest as noise.
- **The break test is a deceleration, not a shock.** The best break in monthly growth is before 2022-06 (5.5% to 2.6% mean monthly growth, sup-F 8.9 against a critical value of about 8.9). That is borderline, and smooth decay produces it.
- **The ADF-only stationarity table in `05_stats_tests.py` is superseded** by section 7 (ADF and KPSS together, two sample windows). Its "log volume is stationary" reading came from using a constant-only ADF on a trending series and should be ignored. The correlations remain labelled descriptive.
- **Outliers are candidates, not errors.** The flagged months (2019-05, 2020-03 to 2020-05, 2021-05, 2023-11) are mostly COVID waves and festive effects.
- **FY2026-27 is partial** (7 months). Its +23% volume growth compares the same 7 months of the prior year.
- **About 75 monthly points.** Wide intervals everywhere are real. Do not read precision into the point estimates.

## 5. Suggested next steps

1. Decide on Tata Neu and Tata Pay (see section 3).
2. Check FamPay 2023-02 and Bharat Pe 2025-09 against NPCI's original release.
3. Decide whether to estimate the missing PhonePe and Google Pay value for 2022-02 and 2022-03. Current analysis excludes them.
4. If you present this, lead with findings 2, 3, 6 and 7, which are the best supported and most decision-relevant.

## 6. External events (web search) vs. the data

Search results are secondary sources (news, trade press). Items marked "low confidence" were single-source or on unfamiliar domains and should be checked against primary releases before you cite them.

### Validation: external figures match our cleaned data

| External claim | Our data |
|---|---|
| Paytm UPI share 11.8% (Jan 2024), 9% (Mar 2024), 8.1% (May 2024) | 11.9%, 9.0%, 8.2% |
| PhonePe about 49% and Google Pay about 37% (May 2024) | 49.2% and 37.6% |
| Navi began UPI in Aug 2023; passed Amazon Pay in Aug 2024; passed 1% in Dec 2024 | First data 2023-09; passed Amazon Pay 2024-08; 1% first reached 2024-11 (1.23% in Dec) |
| Navi did 120.41 mn UPI transactions in September (passing Axis) | 120.4 mn in 2024-09, the month it first passed Axis Bank |
| super.money beta in June 2024 | First data 2024-06 |

Agreement is within about 0.1 to 0.6 pp, which supports the brand mapping and the settled-volume choice.

### Events dated against movements in the data

| When | Event | What the data shows |
|---|---|---|
| 2020-11 | NPCI proposes the 30% app share cap; WhatsApp Pay gets approval (limited rollout) | WhatsApp's series switches from `WhatsApp Pay` to `WhatsApp` in 2020-11 |
| 2022-12 | Flipkart completes its separation from PhonePe | Not testable from this data |
| 2023-03 | NPCI allows a 1.1% interchange fee on wallet (PPI) merchant payments | Not tested |
| 2023-08 | Navi starts UPI | First data 2023-09; reaches 4.8% share by 2026-09 (rank 4) |
| 2024-01-31 | RBI restricts Paytm Payments Bank; deadline moved to 2024-03-15 | Paytm share 11.9% (Jan), 10.5% (Feb), 9.0% (Mar), 8.2% (May). Consistent with the event-study result |
| 2024-06 | super.money (Flipkart) beta; all Android users by Aug 2024 | First data 2024-06; 1.7% share by 2026-09 |
| 2024-12-02 | RBI lifts restrictions on Navi Finserv (its lending arm) | Not clearly linked to UPI volume; not tested |
| 2024-12-31 | NPCI extends the 30% cap deadline to 2026-12-31; WhatsApp onboarding limit removed | No significant step in WhatsApp growth (see section 4) |
| 2025-07 | Navi raises about Rs 170 crore in debt | Debt, not equity; no visible link |

### Funding: what I could and couldn't find
- **Navi** is the only app with funding I could date: about Rs 170 crore in debt (July 2025) and a $100 million equity round from Prosus. The Prosus round is reported in August 2026, low confidence. Navi's rise (2023-09 onward) came before either, so funding does not explain it.
- **PhonePe and other apps:** the search returned nothing on PhonePe's 2021 to 2023 rounds, so I can't link funding to PhonePe's share gain.
- **Conclusion:** in this data, regulation and product launches explain the visible movements far better than funding rounds. A funding-to-share analysis isn't supported by what I found.

### Status of earlier low-confidence items (second validation round)
- **RBI cancelled Paytm Payments Bank's licence: confirmed.** Effective close of business on 2026-04-24, under Section 22(4) of the Banking Regulation Act, per the RBI press release and several outlets. Paytm says its UPI service continues.
- **UPI merchant fee: confirmed by many outlets, not by the primary circular.** A 0.4% fee on person-to-merchant payments above Rs 2,000 from 2026-10-15, capped at Rs 300 and paid by the merchant. Small merchants (up to Rs 1 lakh a month on UPI QR) and P2P transfers are exempt. Single-source details (a flat Rs 5 for essential categories, 0.02% for capital-market payments) are unconfirmed.
- **30% cap deadline beyond 2026-12-31: still unknown.** I found nothing after the 2024-12-31 announcement.
- **Navi's Prosus round: unchanged (low confidence).**

### Second validation round: previously unchecked items

| Item | External figure | Our data |
|---|---|---|
| super.money volume | 139.10 mn (Feb 2025), 218.96 mn (Jun 2025), 252.85 mn (Jul 2025), 264.79 mn (Oct 2025) | 139.1, 219.0, 252.8, 264.8 mn |
| super.money share plateau | about 1.3% from July to December 2025 | 1.32% to 1.36% |
| Google Pay, Sep 2025 | 683 crore transactions (6.83 bn) | 6,833 mn |
| WhatsApp volume | 74.6 mn (Jul 2025), about 150 mn (Jun 2026), 167.9 mn (Jul 2026) | 74.6, 150.5, 167.9 mn |
| WhatsApp share | about 0.27% (mid-2024), about 0.7% (Jun 2026) | 0.27% (2024-06), 0.67% (2026-06) |
| Top-3 share (PhonePe, Google Pay, Paytm) | 95.2% (Jan 2024), 88.3% (Jul 2025) | 95.3%, 89.9% |
| PhonePe, Google Pay, Paytm, Navi, super.money, Jun 2025 | 46.46%, 35.56%, 6.9%, 2.21%, 1.19% | 47.2%, 36.1%, 7.0%, 2.24%, 1.21% |

- **Volumes match to the decimal** (super.money, Google Pay, WhatsApp), which confirms that brand mapping and aggregation are correct for these apps.
- **Shares run about 1.6% higher in relative terms than NPCI's** (for example PhonePe 47.2% vs 46.46%). NPCI divides by total UPI volume, and I divide by the sum of listed apps, which is about 1.6% lower than the headline in late 2025. Trends are unaffected, but if you quote a specific share, divide by headline volume to match NPCI.
- **WhatsApp after the cap removal:** one outlet reports a "muted 17% rise". Ours shows +5.4% in January 2025 over December, so the direction is consistent with the "not detectable" test result, but the 17% figure uses an undefined window and I could not reproduce it.
- **Not verifiable:** I found no external per-bank-app volumes (SBI, HDFC, ICICI, Axis, Kotak), so those series stand unvalidated. One anomaly to inspect: ICICI Bank falls from 72.5 mn (Dec 2025) to 40.0 mn (Feb 2026) and only partly recovers (62.0 mn in Apr 2026), while Kotak rises steadily from 67 to 116 mn. This is plausibly a PSP-bank arrangement change, not a data error, but I can't confirm it.
- **One conflicting report:** one source puts super.money at 1.8% in May 2026. Ours is about 1.6% and rising, and the plateau report (1.3%) matches 2025 exactly. I treat the 1.8% figure as probably a different basis.

### Is the October 2026 fee visible in the data yet?
No. September to October per-day volume growth was +2.4% in 2026, against +4.6% (2023), +6.7% (2024) and +2.0% (2025). P2M share moved -0.08 pp (normal range: -0.06 to +0.33), and the ticket rose 1.4%. The fee applied for only 17 days of October, and the festive calendar moves, so this is too early to read. November and December will be the first clean months.

### The cap deadline matters for this project
The 30% cap compliance date is 2026-12-31. In our data (2026-09), PhonePe has 45.6% and Google Pay 32.2%, both over the cap. If the cap is enforced without another extension, the "stable duopoly" finding would be tested within weeks. This is worth a line in any presentation.

## 7. Time series diagnostics (before forecasting)

Script: `06_timeseries_diagnostics.py`. Charts 11 to 13, table `data/ts_diagnostics.csv`. Target series: log of volume per day.

| Check | Full sample (91 months) | Post-COVID (2021-06 on, 65 months) |
|---|---|---|
| Log level, ADF + KPSS | Not stationary (KPSS rejects; the ADF "stationary" reading is an artifact of testing a trend with a constant only) | Same |
| Monthly growth (d log) | **Not stationary** (ADF p = 0.95, KPSS p = 0.02) | **Not stationary** (ADF p = 0.08, KPSS p = 0.01) |
| Growth, seasonally differenced | Stationary (ADF 0.034, KPSS 0.09) | Not stationary (ADF 0.055, KPSS 0.04) |
| Best ARIMA(p,1,q)+drift by AIC | (0,1,1) | (2,1,2) |
| Residual autocorrelation (Ljung-Box lag 12 / 24) | Passes (p = 0.24 / 0.13) | Passes (p = 0.20 / 0.13) |
| Residual variance (ARCH test) | **Fails** (p < 0.001); variance 11.9x higher in the first half | Passes (p = 0.52); variance 2.1x higher in the first half |
| Residual normality (Jarque-Bera) | Fails (p < 0.001) | Fails, mildly (p = 0.002) |

### What this means for the forecast
1. **One difference is not enough.** Growth itself is decaying, so its mean is not constant. A standard ARIMA(p,1,q) with drift assumes constant growth and will **over-forecast**. Use a damped-trend model (ETS with damping), ARIMA with d=2, or model the growth rate with an explicit decay.
2. **Train on the post-COVID window.** The full sample fails the heteroskedasticity check badly (COVID-era variance is about 12x). Intervals from it would be wrong. The post-COVID window passes autocorrelation and ARCH checks.
3. **Volatility is still falling.** Monthly growth std went from 2.6% to 1.8% across the post-COVID window, so pooled-variance intervals will be somewhat too wide. That is conservative, not dangerous.
4. **Trend dominates; seasonality is a second-order effect.** STL trend strength is 0.88 to 1.00 for every series. Seasonal strength: volume 0.38, ticket 0.27, top-2 share 0.14, value 0.09, P2M share 0.00, banks live 0.00. Only volume merits seasonal terms. Forecast value as volume x ticket, not directly.
5. **Autocorrelation is partly an artifact.** Post-COVID ACF shows significant lags 1, 2, 4 to 7 and 12, but this is largely the decaying mean leaking in. The PACF (significant at lags 1 and 2) is the more reliable guide, which supports small AR terms.
6. **Growth is only moderately predictable.** Mean growth is 3.4% a month with std 2.55% (signal-to-noise 1.33), and lag-1 autocorrelation is 0.27. Expect useful point forecasts for a few months and wide intervals beyond that.

### Caveats
- The AIC-selected ARIMA(2,1,2) on 65 points likely overfits, and some candidate fits reported convergence warnings. Treat the selected orders as a starting point, not an answer.
- KPSS p-values at the table's boundary (0.01 or 0.10) are truncated; the true values are further out.
- Only 65 post-COVID points leave little room for a holdout. The backtest should use rolling origins with short horizons.

## 8. Forecast (next 12 months: 2026-11 to 2027-10)

Script: `07_forecast.py`. Charts 14 to 16. Tables `data/forecast_12m.csv` (forecast with 80% and 95% intervals) and `data/forecast_backtest.csv`.

### Method
- Trained on 2021-06 to 2026-10 (post-COVID window, see section 7).
- Eight models compared with an expanding-window, rolling-origin backtest (first origin after 36 months; 28 origins at 1 month ahead, 18 at 12 months), scored by MAPE, bias, MASE and 80% interval coverage.
- Volume per day uses ETS with a damped trend and additive seasonality. Average ticket uses ETS with a damped trend and no seasonality. Value = volume x ticket / 10. Intervals come from 4,000 simulated paths.

### Backtest results (volume)
| Horizon | Best model | MAPE | Bias | 80% interval coverage | Best baseline MAPE |
|---|---|---|---|---|---|
| 1 month | ETS damped | 1.3% | -0.4% | 89% | drift 1.3% |
| 3 months | ETS damped + seasonal | 1.8% | -0.8% | 81% | drift 1.95% |
| 6 months | ETS damped + seasonal | 2.1% | -1.7% | 83% | drift 3.2% |
| 12 months | ETS damped + seasonal | 4.0% | -3.8% | 89% | drift / seasonal naive 8.5% |

- The damped model beats every baseline from 3 months out. At 12 months its error is about half the baselines' (4.0% vs 8.5%).
- **Constant-growth models over-forecast**: drift and seasonal-naive +8.5% at 12 months, ARIMA(1,2,1) +5.8%, decaying-growth +14%. This confirms the section 7 warning. The decaying-growth model is the worst and its intervals cover only 6% of outcomes at 12 months, so don't use it.
- The chosen model slightly **under**-forecasts (-3.8% at 12 months), so treat the central forecast as a mildly conservative one.
- Ticket: the seasonal variant wins at short horizons but its intervals cover only 17 to 54%, so I used the non-seasonal damped model, which has 75 to 83% coverage at 3 to 12 months.

### Forecast (median, 80% interval)
| Month | Volume (mn) | Avg ticket (Rs) | Value (Rs lakh crore) | Volume YoY |
|---|---|---|---|---|
| 2026-11 | 24,407 (23,976 to 24,845) | 1,234 | 30.1 | 19.3% |
| 2027-03 | 26,597 (25,763 to 27,485) | 1,218 | 32.4 | 17.5% |
| 2027-10 | 28,927 (27,512 to 30,387) | 1,197 | 34.6 | 13.6% |

- **YoY volume growth is forecast to keep falling**, from 23.0% in 2026-10 to about 13.6% by 2027-10.
- **FY2026-27 volume** (actual Apr to Oct plus forecast Nov to Mar): about 291,600 mn, +20.7% on FY2025-26 (80% interval +19.6% to +21.9%). **Value**: about Rs 362.6 lakh crore, +15.4% (80%: +12.8% to +18.2%).
- Average ticket is forecast to drift down from Rs 1,238 to about Rs 1,197, continuing the mix effect from section 1b.

### Limits of this forecast
1. **Status quo assumed.** The forecast knows nothing about the 30% market-share cap (deadline 2026-12-31) or the 0.4% UPI merchant fee on payments above Rs 2,000 (effective 2026-10-15, now confirmed by multiple outlets). The fee targets P2M, the segment driving growth, and could slow volume or push some payments to cash. A policy shock would be outside the intervals. Treat the November to December 2026 actuals as the first real test of this forecast.
2. **Festival dates move.** Seasonality is by calendar month, so a festival shifting between October and November misallocates volume. The November 2026 forecast being lower than the October actual partly reflects this.
3. **Value intervals are approximate.** Volume and ticket errors had a backtest correlation of 0.20, but the simulation treats them as independent, so value intervals are somewhat too narrow.
4. **Short backtest.** At 12 months ahead only 18 origins are available, and they overlap, so the 12-month error and coverage numbers are rough.
5. **Beyond about 6 months** the intervals widen quickly and the forecast is a trend extrapolation, not a prediction of specific months.
6. **A bug caught along the way:** an early run reported near-zero interval coverage because of a pandas averaging problem with mixed boolean/NaN columns. It's fixed; the numbers above are the corrected ones.
