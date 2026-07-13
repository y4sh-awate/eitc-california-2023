# eitc-california-2023

Replication code for *The Effective Tax Burden of Low- and Moderate-Income California Households: A Quantitative Analysis of the Federal EITC and CalEITC* (Awate 2026). The paper is available on SSRN at [link to be added once posted].

## Overview

This repository contains the Python pipeline that computes effective tax rates and implicit marginal tax rates for California households across the $1,000 to $75,000 income range under tax year 2023 federal and California tax law. The pipeline reproduces every numeric result reported in Sections 6 and 7 of the paper.

The analysis covers four household types: single filer with no qualifying children, head of household with one qualifying child, head of household with two or more qualifying children, and married filing jointly with qualifying children. For each household type, the pipeline computes federal income tax, California income tax, employee-side payroll tax, the federal Earned Income Tax Credit, the refundable Additional Child Tax Credit, the nonrefundable Child Tax Credit, the California Earned Income Tax Credit, and the Young Child Tax Credit at every $1,000 increment of earned income.

## Files

- `etr_pipeline.py` — the full pipeline. Computes net effective tax rates, implicit marginal tax rates, and writes the two output CSVs.
- `section6_etr_results.csv` — gross, post-federal, and net effective tax rates by income level and household type. Reproduces Table 1 of the paper.
- `section7_cliff_analysis.csv` — implicit marginal tax rates at $1,000 increments, with cliff and notch flags. Reproduces the cliff analysis in Section 7.

## Reproducing the results

Requires Python 3.8 or later. No external dependencies beyond the standard library.

```
python etr_pipeline.py
```

The script writes the two CSV files to the working directory and prints a summary of key findings to stdout.

## Parameter sources

All tax-year 2023 parameters are verified against primary sources. Federal EITC schedules, CTC, ACTC, federal income tax brackets, and the federal standard deduction are taken from IRS Revenue Procedure 2022-38. California EITC anchor points, the $30,950 earned-income and AGI cap, Young Child Tax Credit, and Foster Youth Tax Credit parameters are taken from the California Franchise Tax Board's 2023 Form 3514 booklet, including the published 2023 Earned Income Tax Credit Table. California income tax brackets, standard deduction, and personal exemption credits are taken from the FTB 2023 Tax Rate Schedules. The Social Security wage base and payroll tax rates are taken from the Social Security Administration's 2023 Social Security Changes Fact Sheet. Source citations and exact parameter values are documented inline in `etr_pipeline.py`.

## Methodology notes

The CalEITC is computed by piecewise-linear interpolation over anchor points read directly from the 2023 Earned Income Tax Credit Table published in the FTB Form 3514 booklet (`CALEITC_ANCHORS` in `etr_pipeline.py`), with the $30,950 earned-income and AGI cap enforced as a hard cutoff. The anchors are not reconstructed from a formula; the published table is the primary source. The phase-out is a two-segment piecewise structure: a steep segment from each category's peak down to approximately $16,700–$16,900 of earned income, followed by a shallow tail of roughly 3 to 4 percent that reaches $1 at approximately $30,925.

The pipeline assumes statutory incidence for payroll tax (employee share only) and does not model the employer share. Sales tax, Medi-Cal, CalFresh, child care subsidies, and housing assistance are not modeled; these extensions are flagged in Section 9 of the paper as open avenues.

The output columns `CTC_Nonref` and `ACTC` reflect a refundable-first decomposition of the Child Tax Credit: the refundable portion is computed first (15% of earned income above $2,500, capped at $1,600 per child) and the nonrefundable remainder is then applied against income tax liability. This ordering yields a combined credit identical to the statutory liability-first ordering at every grid point, so all net effective tax rates are unaffected; only the split between the two columns depends on the convention.

The Foster Youth Tax Credit is not modeled in the baseline calculation because its eligibility population (current or former foster youth aged 18–25) is not separable from the four-category household segmentation used in the paper. Its phase-out parameters are identical to the YCTC.

## Citation

If you use this code or its outputs, please cite the paper:

> Awate, Yash. 2026. *The Effective Tax Burden of Low- and Moderate-Income California Households: A Quantitative Analysis of the Federal EITC and CalEITC.* SSRN Working Paper [number to be added].

## License

MIT License. See `LICENSE` for details.

## Contact

Questions about the code or the paper can be sent to yashawate@gmail.com.
