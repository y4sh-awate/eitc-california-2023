# eitc-california-2023
Replication code for The Effective Tax Burden of Low- and Moderate-Income California Households: A Quantitative Analysis of the Federal EITC and CalEITC (Awate 2026). The paper is available on SSRN at [link to be added once posted].
Overview
This repository contains the Python pipeline that computes effective tax rates and implicit marginal tax rates for California households across the $1,000 to $75,000 income range under tax year 2023 federal and California tax law. The pipeline reproduces every numeric result reported in Sections 6 and 7 of the paper.
The analysis covers four household types: single filer with no qualifying children, head of household with one qualifying child, head of household with two or more qualifying children, and married filing jointly with qualifying children. For each household type, the pipeline computes federal income tax, California income tax, employee-side payroll tax, the federal Earned Income Tax Credit, the refundable Additional Child Tax Credit, the nonrefundable Child Tax Credit, the California Earned Income Tax Credit, and the Young Child Tax Credit at every $1,000 increment of earned income.
Files
etr_pipeline.py — the full pipeline. Computes net effective tax rates, implicit marginal tax rates, and writes the two output CSVs.
section6_etr_results.csv — gross, post-federal, and net effective tax rates by income level and household type. Reproduces Table 1 of the paper.
section7_cliff_analysis.csv — implicit marginal tax rates at $1,000 increments, with cliff and notch flags. Reproduces the cliff analysis in Section 7.
Reproducing the results
Requires Python 3.8 or later. No external dependencies beyond the standard library.
python etr_pipeline.py
The script writes the two CSV files to the working directory and prints a summary of key findings to stdout.
Parameter sources
All tax-year 2023 parameters are verified against primary sources. Federal EITC schedules, CTC, ACTC, federal income tax brackets, and the federal standard deduction are taken from IRS Revenue Procedure 2022-38. California EITC, Young Child Tax Credit, and Foster Youth Tax Credit parameters are taken from the California Franchise Tax Board's 2023 California Earned Income Tax Credit and Young Child Tax Credit Report. California income tax brackets, standard deduction, and personal exemption credits are taken from the FTB 2023 Tax Rate Schedules. The Social Security wage base and payroll tax rates are taken from the Social Security Administration's 2023 Social Security Changes Fact Sheet. Source citations and exact parameter values are documented inline in etr_pipeline.py.
Methodology notes
The CalEITC phase-in and phase-out anchor points used in the pipeline are reconstructed from the FTB-published category maximums and the $30,931 earned-income cap. They reproduce the published category maximums to within rounding and produce cliff identifications that are robust to perturbations in the anchor points of several hundred dollars per category. Users with access to the FTB Form 3514 lookup table can substitute exact anchor points without altering the pipeline structure.
The pipeline assumes statutory incidence for payroll tax (employee share only) and does not model the employer share. Sales tax, Medi-Cal, CalFresh, child care subsidies, and housing assistance are not modeled; these extensions are flagged in Section 9 of the paper as open avenues.
The Foster Youth Tax Credit is not modeled in the baseline calculation because its eligibility population (current or former foster youth aged 18–25) is not separable from the four-category household segmentation used in the paper.
Citation
If you use this code or its outputs, please cite the paper:
Awate, Yash. 2026. The Effective Tax Burden of Low- and Moderate-Income California Households: A Quantitative Analysis of the Federal EITC and CalEITC. SSRN Working Paper [number to be added].
License
MIT License. See LICENSE for details.
Contact
Questions about the code or the paper can be sent to yashawate@gmail.com.
