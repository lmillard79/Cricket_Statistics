Cricket grounds as hydrological gauges: preliminary findings and way forward
Status: Working draft — not for distribution
Purpose: Weekend review and planning note

# 1. What this is
This document records the current state of a thought experiment applying standard Australian flood frequency analysis methods to Test cricket batting records. Each Test ground is treated as a stream gauge. The annual maxima series (AMS) is the highest individual innings score recorded at that ground in any calendar year. The GEV distribution is fitted to each AMS using Bayesian estimation in RMC-BestFit v1.0. Bivariate copula analysis is used to characterise dependence between ground pairs.
The analysis is recreational and illustrative. It is not peer-reviewed. All GEV fits and AEP quantiles are indicative only.
The practical purpose is threefold. First, it tests whether 148 years of Test cricket data behaves sensibly when treated as a hydrological record. Second, it provides a genuinely engaging surrogate for explaining extreme value theory, non-stationarity, and joint probability to non-specialist audiences. Third, it is building toward a LinkedIn article and infographic series connecting flood hydrology concepts to a cricket audience — with deliberate hooks for Indian and Pakistani followers via the IPL 2026 season.

# 2. Data and methods
## 2.1 Data source
Individual innings scores for all Test matches at each ground were extracted from ESPNcricinfo Statsguru via web scraping. The query returns every individual innings in chronological order, allowing annual maxima to be computed from the full historical record.
## 2.2 Grounds selected
GroundCountryFirst TestRecord startMCGAustralia18771877GabbaAustralia19311931Lord'sEngland18841884HeadingleyEngland18991899Eden GardensIndia19341934 — pending
Eden Gardens data has been extracted but not yet processed through RMC-BestFit. This remains a priority task.
## 2.3 AMS construction
For each ground, the highest individual innings score in each calendar year was extracted. Years with no Test at that ground were excluded rather than interpolated. The resulting AMS is unequally spaced in time, which is a known limitation discussed further in Section 5.
## 2.4 GEV fitting
The GEV was fitted using RMC-BestFit v1.0, employing Bayesian estimation with default flat priors. Low outlier tests were applied to all datasets. RMC-BestFit identified and flagged low outliers at the MCG (3 points), Gabba (3 points) and Lord's (4 points). Headingley had no flagged low outliers. Low outlier points are shown as red crosses in the frequency plots and are excluded from the main fit.
The Bayesian framework produces three outputs for each ground: the posterior mode (the single best-fit curve), the posterior predictive (the mean of the predictive distribution), and 90% credible intervals.
## 2.5 Bivariate analysis
Three ground pairs were analysed using the bivariate copula analysis in RMC-BestFit v1.0:

Lord's vs Headingley (two English grounds)
MCG vs Lord's (cross-hemisphere pair)
MCG vs Gabba (two Australian grounds)

All three analyses used a Normal copula fitted by inference from margins, with a uniform prior on theta in the range (-1, 1).

# 3. Current findings
## 3.1 Sample sizes and ground records
The historical record is substantially longer than the Cricsheet digital record, which only extends to approximately 2001. The ESPNcricinfo scrape recovered the full historical record for all four grounds.
GroundAMS seasonsUsed in GEV fitLow outliersGround record (in data)MCG95843307 runsLord's105994333 runs (Gooch, 1990)Headingley82720334 runs (Hutton, 1938)Gabba64453259 runs
These are genuinely usable records. Lord's at 99 fitted points and the MCG at 84 are comparable to well-gauged Australian catchments used in ARR flood frequency analysis.

## 3.2 GEV posterior mode quantiles
The table below summarises the posterior mode innings score at selected AEP levels. These are the best-estimate design quantiles — the cricket equivalent of a design flood.
AEPReturn periodMCGLord'sHeadingleyGabba50%2 season13314312014320%5 season17518816917910%10 season2022152061995%20 season2282392442172%50 season2622662982381%100 season2862853432520.2%500 season342324463280

## 3.3 Key GEV findings
Headingley is the flashiest catchment. The 1% AEP innings at Headingley (343 runs) is the highest of the four grounds, and the 0.2% AEP extrapolates to 463 runs — well above any other venue. The distribution has a heavy upward tail consistent with Fréchet behaviour. In hydrological terms, Headingley is an unregulated headwaters catchment: low median yield but capable of extreme events that dwarf the historical record. Hutton's 364 in 1938 sits just off the top of the fitted AMS and the GEV credible intervals are consistent with that score being a rare but not impossible event.
Lord's is the most constrained catchment. Despite the longest fitted record (99 points), the 1% AEP at Lord's (285 runs) is the second-lowest. The frequency curve flattens visibly at low AEP, consistent with Weibull-family behaviour and a soft upper bound. Lord's reputation for helping seamers and overhead-light dismissals is encoded in the distribution. In hydrological terms, it behaves like a regulated catchment with natural detention — extreme events are dampened relative to other venues. Gooch's 333 is an exception that pulls the posterior predictive upward; the posterior mode curve treats it as a genuine outlier in the upper tail.
The MCG is the benchmark stable catchment. With 84 fitted points spanning 148 years, the MCG produces the most statistically stable result. The distribution is near-Gumbel (shape near zero), confidence intervals are the tightest of the four grounds, and the progression from median to rare quantiles is smooth and physically sensible. The 307 ground record sits at approximately 0.7% AEP on the posterior mode curve.
The Gabba remains limited by record length. At 45 fitted points from 1931, the Gabba produces the widest confidence intervals of the four grounds. The 1% AEP (252 runs) is the lowest, which likely reflects the shorter record rather than a genuinely lower extreme potential. The Gabba's flat-pitch reputation is primarily a post-1990 phenomenon; the earlier decades of lower scoring suppress the fitted quantiles.
The England drought signal is visible but nuanced. The 50% AEP innings at Headingley (120 runs) is the lowest median of all four grounds — meaning half of all season-peak innings there are below 120 runs. Lord's median (143) is also lower than both Australian grounds. However, the drought framing is most defensible at the median level. At rare AEPs, Headingley actually produces higher design quantiles than Australia, not lower. The drought is a central tendency effect, not a tail effect.

## 3.4 Bivariate copula findings
The three probability contour plots reveal the dependence structure between ground pairs. The key quantity is theta — the Normal copula correlation parameter. These values need to be read from the Tabular Results tab in RMC-BestFit for each analysis. Extracting theta is a priority task before the write-up is finalised.
Qualitative observations from the plots:
Lord's vs Headingley shows the most compact data cloud of the three pairs, suggesting moderate positive dependence. When English summer conditions favour batting at one ground, they tend to favour batting at both. This is the shared-climate signal. The two extreme outliers (a very high Headingley season with a low Lord's score, and vice versa) sit in very different probability space, indicating that the most extreme individual events are driven by ground-specific factors — pitch preparation, match scheduling, opposition quality — rather than the shared climate.
MCG vs Lord's shows the most dispersed data cloud, consistent with near-independence between hemispheres. A big batting year in Melbourne carries essentially no information about what will happen at Lord's. This is physically expected — Southern Hemisphere summer and Northern Hemisphere summer are independent climatic systems.
MCG vs Gabba appears intermediate. Both Australian grounds share a climate signal, but the shorter Gabba record limits the strength of this inference.
The practical implication: joint probability matters for the Ashes drought narrative. If Lord's and Headingley were strongly correlated, a drought at both simultaneously would be far more probable than the product of their individual probabilities. The visual evidence suggests moderate rather than strong correlation, which means joint droughts are possible but not the dominant mode of failure.

# 4. The PMF analogue
In each ground's frequency plot, the ground record is marked as a horizontal reference line — the Probable Maximum Innings. This is the cricket equivalent of the PMF in flood hydrology: the deterministic upper bound of observed performance at that location.
The parallel is instructive. Just as the PMF in hydrology is defined by the historical observational record and the methods used to estimate it (PMP), the ground record in cricket is defined by the conditions that prevailed on a single day under a specific combination of pitch, weather, opposition bowling attack, and match context. In neither case does the deterministic upper bound carry a well-defined annual exceedance probability.
The GEV curve approaches but never reaches the ground record in the probability domain. Extrapolation beyond the record length is always uncertain — this is why the posterior predictive diverges from the posterior mode at low AEP. This is identical to the behaviour seen in ARR-compliant frequency analysis when the fitted curve is extrapolated beyond the period of record.
Gooch's 333 at Lord's and Hutton's 334 at Headingley represent approximately 1–2% AEP events on the respective fitted curves. They are rare, but the GEV says they are within the expected range of the distribution — not physically impossible outliers. This is the correct hydrological interpretation of a very large but real observed event.

# 5. Limitations
The iid assumption. RMC-BestFit requires block annual maxima to be independent and identically distributed. The AMS almost certainly violates this assumption in at least two ways. First, consecutive years sharing the same set of players and the same batting culture are not independent in the strict statistical sense — a good batting generation produces correlated high scores across multiple seasons. Second, the identical distribution assumption is the non-stationarity question: the distribution has almost certainly shifted across 148 years as batting techniques, equipment, pitch preparation, and match scheduling have evolved.
Unequally spaced record. Not every ground hosts a Test every year. The Gabba hosts roughly one to two Tests per Australian summer, which is one AMS point per year in some decades and a gap in others. The GEV fitting treats the available AMS points as the complete record, which is correct, but the effective record length is shorter than the calendar span suggests.
Ground record understatement. For all four grounds, the ground record in this dataset is the highest score in the ESPNcricinfo Statsguru record, which may not be the all-time ground record if earlier scorecards contain errors or incomplete ball-by-ball data. The MCG all-time record may be higher than 307 for innings played in the pre-digital era.
Eden Gardens pending. India's oldest Test ground is not yet included in the frequency analysis. The omission matters for the Indian and Pakistani audience engagement strategy and for the bivariate analysis — an Eden Gardens vs MCG copula would be the most geographically interesting cross-hemisphere comparison.

# 6. Way forward — priority tasks
## 6.1 Immediate (before publishing)
Extract theta values from RMC-BestFit tabular results for all three copula analyses. This is the single most important missing piece. Theta quantifies the dependence strength and is needed to make the joint probability narrative precise. Open each bivariate analysis, click Tabular Results, and record the posterior estimate and credible interval for theta.
Run Eden Gardens through RMC-BestFit. The data has been extracted. Load it as a new dataset, apply the GEV fit, flag low outliers, and record the posterior mode quantiles and ground record AEP. VVS Laxman's 281 in 2001 will almost certainly sit in the upper tail and may flag as a high outlier — that is a good story in itself.
Run MCG vs Eden Gardens bivariate analysis. This is the Australia vs India joint probability plot. It will be the most engaging graphic for the Indian audience.

## 6.2 Short term (RMC-BestFit v2.0 Beta exploration)
Download and install RMC-BestFit v2.0 Beta from the USACE RMC website. The v2.0 release includes non-stationarity analysis as a new feature. The documentation has not yet caught up with the software, but the feature list confirms it exists.
Run hypothesis testing on the MCG AMS. With 95 seasons from 1877, the MCG has the statistical power to detect a trend. In v2.0, load the MCG dataset with the year column included, then look for hypothesis testing or trend test options in the analysis menu. The Mann-Kendall test will report whether a monotonic trend is present. A positive result means the "climate" of MCG batting has warmed — the distribution has shifted upward over time.
Attempt a nonstationary GEV fit for the MCG. If v2.0 supports it (the feature list suggests it does), fit a GEV where the location parameter mu is allowed to vary linearly with time. The output will give you mu(t) = mu0 + mu1 × t. If mu1 is positive with credible intervals excluding zero, the non-stationarity is statistically confirmed. This is the quantitative finding that makes the whole analysis publishable at HWRS standard.
Repeat for Lord's. Lord's at 99 fitted seasons is the second strongest record and the most interesting ground for the non-stationarity story — if the distribution has shifted at Lord's, it is likely a genuine signal of changing Test match batting culture rather than a home-ground effect.

## 6.3 Medium term (HWRS 2026 potential)
The analysis in its current form is a thought experiment. With the following additions it becomes a defensible conference paper:

Formal non-stationarity testing with documented results from RMC-BestFit v2.0 or equivalent software
Eden Gardens included, completing the five-ground comparison
Theta values from all copula analyses, with physical interpretation
A brief literature review connecting cricket batting distributions to EVT applications in sports statistics — this field exists and provides methodological grounding
A clear statement of the pedagogical purpose: the analysis is a surrogate for teaching extreme value concepts, not a claim that cricket is hydrology

The paper would sit naturally in the "innovations in hydrological education and communication" category if HWRS 2026 has such a session. If not, it fits within extreme value methods as a novel application.

## 6.4 LinkedIn publication strategy
The analysis supports a two-part LinkedIn publication sequence.
Part 1 — The concept post (ready now). The flash flood versus drought framing, Suryavanshi at SR 249 as the non-stationary outlier, Tendulkar as reliable baseflow, the England drought signal at the median. This post works without the formal analysis and can go out on a Sunday while the deeper work continues. The Nano Banana infographic supports this post.
Part 2 — The full analysis post (after RMC-BestFit v2.0 non-stationarity work is complete). The five-ground frequency curves, the copula contour plots, the theta values, the non-stationarity test results, and the PMF analogue framing. This post will be longer and more technical but will find a specific audience among flood frequency practitioners who will immediately recognise the methodology and find the application genuinely surprising.

# 7. Suggested structure for the full LinkedIn article
When the analysis is complete, the article structure should follow this sequence:
Opening. A provocative framing statement connecting cricket scoring to flood hydrology. Not a question — a statement that makes the reader stop. Something like: "148 years of Test match innings data fits a GEV distribution. Not approximately. Properly."
The surrogate framework. Two short paragraphs explaining the catchment analogy. Ground as gauge station, innings as flood event, annual maxima series, GEV fit. Keep this tight — practitioners will understand immediately and non-practitioners need only enough to follow the results.

The univariate findings. The four-ground comparison table and the key narrative points: Headingley's heavy tail, Lord's constraint, MCG stability, the England drought as a median effect not a tail effect.
The PMF analogue. Gooch's 333 and Hutton's 334 as the Probable Maximum Innings. Connect this explicitly to the PMF paper being developed for HWRS 2026 — this is an opportunity to cross-promote the main research thread.
The joint probability findings. The copula plots and theta values. The English grounds share a climate signal; the hemispheres are independent. What this means for understanding the Ashes drought as a systemic versus local phenomenon.
Non-stationarity. The unfinished business. Report the Mann-Kendall test result and the nonstationary GEV parameter trend honestly, including the uncertainty. Invite practitioners to engage with the methodology.
The honest caveat. The iid assumption, the short Gabba record, the pedagogical rather than predictive purpose. This is a thought experiment in the tradition of Tony Ladson's blog — rigorous enough to be interesting, honest enough to be trusted.
Close. A genuine question inviting engagement. Something directed at the flood frequency community: "If you were explaining non-stationarity to a client who had never heard of a GEV distribution, what would you reach for?"

# 8. Data files and software state
FileDescriptionStatusams_per_ground.csvAnnual maxima series for all five groundsCompleteMCG-fitted.csvRMC-BestFit tabular output, MCGCompleteLords-fitted.csvRMC-BestFit tabular output, Lord'sCompleteHeadingley-fitted.csvRMC-BestFit tabular output, HeadingleyCompleteGabba-Fitted.csvRMC-BestFit tabular output, GabbaCompleteground_innings_historical.csvFull ESPNcricinfo scrape, all groundsCompleteEden Gardens fitRMC-BestFit tabular output, Eden GardensPendingCopula theta valuesExtracted from Tabular Results tabPendingNon-stationarity resultsRMC-BestFit v2.0 BetaPendingplot_grounds_gev.pngFive-panel frequency curve figureComplete (v1)Bivariate copula plotsThree PNG exports from RMC-BestFitComplete
Software state

RMC-BestFit v1.0: used for all current GEV fits and bivariate analyses. Project file saved locally.
RMC-BestFit v2.0 Beta: available for download from USACE RMC website. Not yet installed. Required for non-stationarity analysis.
Windsurf: Python environment with Cricsheet data extracted to d:\GitRepos\CricketPMF\. Code for AMS construction, GEV fitting, and plotting is complete. ESPNcricinfo scraper is functional.


# 9. References and data sources
Data

ESPNcricinfo Statsguru — innings-by-innings batting records for all Test grounds
Cricsheet tests_json.zip — ball-by-ball JSON records for Tests from 2001

**Software**

RMC-BestFit v1.0, US Army Corps of Engineers Risk Management Center
RMC-BestFit v2.0 Beta, USACE RMC (pending installation)

## Methods

Hosking, J.R.M. and Wallis, J.R. (1997) Regional Frequency Analysis: An Approach Based on L-Moments. Cambridge University Press.
Ball, J. et al. (eds) (2019) Australian Rainfall and Runoff: A Guide to Flood Estimation. Geoscience Australia.
Smith, C.H. and Daughty, M. (2020) RMC-BestFit Quick Start Guide. USACE RMC Technical Report RMC-TR-2020-03.

# Inspiration

Ladson, A.R. — tonyladson.wordpress.com — hydrology blog applying statistical methods to non-hydrological problems


End of preliminary write-up. Prepared April 2026. Return to this document after RMC-BestFit v2.0 Beta exploration and Eden Gardens analysis.
