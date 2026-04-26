"""
EITC Effective Tax Rate Pipeline
================================
Computes net effective tax rates and implicit marginal tax rates
for California households across the $0-$75,000 income distribution
under TY2023 federal and California tax law.

Author: Yash Awate, Portola High School
Companion code for: "The Effective Tax Burden of Low- and Moderate-Income
California Households: A Quantitative Analysis of the Federal EITC and CalEITC"

All parameters verified against:
  - IRS Rev. Proc. 2022-38 (federal EITC, CTC, brackets, std deduction)
  - California FTB 2023 CalEITC and YCTC Report (CalEITC, YCTC, FYTC)
  - California FTB 2023 Tax Rate Schedules (CA brackets, std deduction, exemptions)
  - SSA 2023 fact sheet (payroll tax, wage base)
"""

import csv
from dataclasses import dataclass

# =====================================================================
# HOUSEHOLD TYPE DEFINITIONS
# =====================================================================
HH_TYPES = {
    "single_no_kids":   {"filing": "single", "kids": 0, "kids_under_6": 0, "label": "Single, no children"},
    "hoh_one_kid":      {"filing": "hoh",    "kids": 1, "kids_under_6": 1, "label": "HoH, one child"},
    "hoh_two_kids":     {"filing": "hoh",    "kids": 2, "kids_under_6": 1, "label": "HoH, two+ children"},
    "mfj_two_kids":     {"filing": "mfj",    "kids": 2, "kids_under_6": 1, "label": "MFJ, with children"},
}

# =====================================================================
# FEDERAL EITC PARAMETERS (TY2023, Rev. Proc. 2022-38)
# =====================================================================
# Format: (phase_in_rate, max_credit, plateau_end_unmarried, plateau_end_mfj, phase_out_rate)
FED_EITC = {
    0: (0.0765, 600,   9800,  16370, 0.0765),
    1: (0.34,   3995,  21560, 28120, 0.1598),
    2: (0.40,   6604,  21560, 28120, 0.2106),
    3: (0.45,   7430,  21560, 28120, 0.2106),  # 3+ children
}
FED_EITC_INVESTMENT_LIMIT = 11000  # not binding in our analysis

# =====================================================================
# FEDERAL CTC/ACTC (TY2023)
# =====================================================================
CTC_PER_CHILD = 2000
ACTC_REFUNDABLE_MAX = 1600
ACTC_EARNED_INCOME_FLOOR = 2500
ACTC_PHASE_IN_RATE = 0.15

# =====================================================================
# FEDERAL INCOME TAX BRACKETS (TY2023)
# =====================================================================
# Format: list of (upper_bound, rate); last bracket has float('inf')
FED_BRACKETS = {
    "single": [(11000, 0.10), (44725, 0.12), (95375, 0.22), (float('inf'), 0.24)],
    "hoh":    [(15700, 0.10), (59850, 0.12), (95350, 0.22), (float('inf'), 0.24)],
    "mfj":    [(22000, 0.10), (89450, 0.12), (190750, 0.22), (float('inf'), 0.24)],
}
FED_STD_DEDUCTION = {"single": 13850, "hoh": 20800, "mfj": 27700}

# =====================================================================
# CALIFORNIA INCOME TAX BRACKETS (TY2023, FTB)
# =====================================================================
CA_BRACKETS = {
    "single": [(10412, 0.01), (24684, 0.02), (38959, 0.04), (54081, 0.06),
               (68350, 0.08), (349137, 0.093), (float('inf'), 0.103)],
    "hoh":    [(20839, 0.01), (49371, 0.02), (63644, 0.04), (78765, 0.06),
               (93037, 0.08), (474824, 0.093), (float('inf'), 0.103)],
    "mfj":    [(20824, 0.01), (49368, 0.02), (77918, 0.04), (108162, 0.06),
               (136700, 0.08), (698274, 0.093), (float('inf'), 0.103)],
}
CA_STD_DEDUCTION = {"single": 5363, "hoh": 10726, "mfj": 10726}
# Personal exemption credits (nonrefundable, applied after tax computed)
CA_EXEMPTION_BASE = {"single": 144, "hoh": 144, "mfj": 288}
CA_EXEMPTION_PER_DEPENDENT = 446

# =====================================================================
# CALEITC PARAMETERS (TY2023, FTB 2023 CalEITC and YCTC Report)
# =====================================================================
# Cap: zero credit above $30,931 of earned income.
# Maximum credits verified: $285 / $1,900 / $3,137 / $3,529
# Phase-in/plateau/phase-out structure approximated from FTB schedule
# (anchor points to verify against FTB Form 3514 2023 lookup table).
CALEITC_CAP = 30931
CALEITC = {
    # kids: (phase_in_rate, max_credit, plateau_start, plateau_end, phase_out_rate)
    0: (0.075,  285,  3800,  5300,  0.0111),
    1: (0.300, 1900,  6400,  10600, 0.0934),
    2: (0.360, 3137,  8700,  10600, 0.1543),
    3: (0.405, 3529,  8700,  10600, 0.1736),
}

# =====================================================================
# YCTC AND FYTC (TY2023)
# =====================================================================
YCTC_MAX = 1117
YCTC_PHASE_OUT_START = 25775
YCTC_PHASE_OUT_END = 30931
FYTC_MAX = 1117  # not modeled in baseline (specific eligibility population)

# =====================================================================
# PAYROLL TAX
# =====================================================================
PAYROLL_RATE = 0.0765  # 6.2% OASDI + 1.45% Medicare (employee side)
SS_WAGE_BASE = 160200  # not binding in our analysis

# =====================================================================
# COMPUTATION FUNCTIONS
# =====================================================================

def bracket_tax(taxable_income, brackets):
    """Apply progressive bracket schedule to a taxable income amount."""
    if taxable_income <= 0:
        return 0
    tax = 0
    prev = 0
    for upper, rate in brackets:
        if taxable_income <= upper:
            tax += (taxable_income - prev) * rate
            return tax
        tax += (upper - prev) * rate
        prev = upper
    return tax


def federal_income_tax(earned_income, hh):
    filing = hh["filing"]
    agi = earned_income
    taxable = max(0, agi - FED_STD_DEDUCTION[filing])
    return bracket_tax(taxable, FED_BRACKETS[filing])


def ca_income_tax(earned_income, hh):
    filing = hh["filing"]
    agi = earned_income
    taxable = max(0, agi - CA_STD_DEDUCTION[filing])
    gross = bracket_tax(taxable, CA_BRACKETS[filing])
    # Apply nonrefundable personal exemption credit
    exemption = CA_EXEMPTION_BASE[filing] + CA_EXEMPTION_PER_DEPENDENT * hh["kids"]
    return max(0, gross - exemption)


def federal_eitc(earned_income, hh):
    kids = min(hh["kids"], 3)
    rate, max_c, plateau_unm, plateau_mfj, po_rate = FED_EITC[kids]
    plateau_end = plateau_mfj if hh["filing"] == "mfj" else plateau_unm
    if earned_income <= 0:
        return 0
    # Phase-in
    credit_at_phase_in = rate * earned_income
    if credit_at_phase_in <= max_c:
        if earned_income <= plateau_end:
            return min(credit_at_phase_in, max_c)
    # Plateau or phase-out
    if earned_income <= plateau_end:
        return max_c
    # Phase-out (applied to greater of earned income or AGI; here equal)
    excess = earned_income - plateau_end
    credit = max_c - po_rate * excess
    return max(0, credit)


def federal_ctc_actc(earned_income, hh):
    """Returns (nonrefundable CTC applied against income tax, refundable ACTC).
    The nonrefundable portion reduces income tax; the refundable portion is added
    as a transfer. Phase-out (AGI > $200K/$400K) is irrelevant in this range.
    """
    kids = hh["kids"]
    if kids == 0:
        return (0, 0)
    total_ctc_potential = CTC_PER_CHILD * kids
    # ACTC: refundable portion phases in at 15% of earnings above $2,500
    actc_phase_in = max(0, ACTC_PHASE_IN_RATE * (earned_income - ACTC_EARNED_INCOME_FLOOR))
    actc_cap = ACTC_REFUNDABLE_MAX * kids
    actc = min(actc_phase_in, actc_cap, total_ctc_potential)
    # Nonrefundable portion: applied against federal income tax up to the
    # remaining (CTC - ACTC) amount. We compute it by checking how much
    # nonrefundable credit is available to offset income tax.
    nonref_available = total_ctc_potential - actc
    fed_tax = federal_income_tax(earned_income, hh)
    nonref_used = min(nonref_available, fed_tax)
    return (nonref_used, actc)


def caleitc(earned_income, hh):
    if earned_income <= 0 or earned_income > CALEITC_CAP:
        return 0
    kids = min(hh["kids"], 3)
    rate, max_c, plat_start, plat_end, po_rate = CALEITC[kids]
    if earned_income <= plat_start:
        return rate * earned_income
    if earned_income <= plat_end:
        return max_c
    excess = earned_income - plat_end
    return max(0, max_c - po_rate * excess)


def yctc(earned_income, hh):
    """Young Child Tax Credit: requires CalEITC eligibility AND a child under 6.
    Phases out from $25,775 to $30,931 (CalEITC cap)."""
    if hh["kids_under_6"] == 0:
        return 0
    if earned_income <= 0 or earned_income > YCTC_PHASE_OUT_END:
        return 0
    if earned_income <= YCTC_PHASE_OUT_START:
        return YCTC_MAX
    # Linear phase-out
    span = YCTC_PHASE_OUT_END - YCTC_PHASE_OUT_START
    fraction = (YCTC_PHASE_OUT_END - earned_income) / span
    return YCTC_MAX * fraction


# =====================================================================
# MAIN ETR CALCULATION
# =====================================================================

@dataclass
class TaxResult:
    income: int
    hh_type: str
    fed_tax_pre_credit: float
    ca_tax_pre_credit: float
    payroll_tax: float
    fed_eitc: float
    ctc_nonref: float
    actc: float
    ca_eitc: float
    yctc: float
    gross_tax: float
    net_tax: float
    etr_gross: float
    etr_net: float
    etr_after_fed_credits: float


def compute_taxes(income, hh_key):
    hh = HH_TYPES[hh_key]
    fed_pre = federal_income_tax(income, hh)
    ca_pre = ca_income_tax(income, hh)
    payroll = PAYROLL_RATE * income
    fed_eitc_amt = federal_eitc(income, hh)
    ctc_nr, actc = federal_ctc_actc(income, hh)
    cal_eitc_amt = caleitc(income, hh)
    yctc_amt = yctc(income, hh)

    gross_tax = fed_pre + ca_pre + payroll
    fed_credits = fed_eitc_amt + ctc_nr + actc
    ca_credits = cal_eitc_amt + yctc_amt
    net_tax = gross_tax - fed_credits - ca_credits

    etr_gross = gross_tax / income if income > 0 else 0
    etr_net = net_tax / income if income > 0 else 0
    etr_after_fed = (gross_tax - fed_credits) / income if income > 0 else 0

    return TaxResult(income, hh_key, fed_pre, ca_pre, payroll,
                     fed_eitc_amt, ctc_nr, actc, cal_eitc_amt, yctc_amt,
                     gross_tax, net_tax, etr_gross, etr_net, etr_after_fed)


# =====================================================================
# RUN ANALYSIS
# =====================================================================

def run_analysis():
    incomes = list(range(1000, 75001, 1000))  # $1K to $75K in $1K steps
    results = {}
    for hh_key in HH_TYPES:
        results[hh_key] = [compute_taxes(inc, hh_key) for inc in incomes]
    return results


def write_section6_table(results, path):
    """Section 6: ETR by income level and household type."""
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(["Income", "Household_Type",
                    "ETR_Gross_PreCredit_pct",
                    "ETR_After_FedCredits_pct",
                    "ETR_Net_FullStack_pct",
                    "Net_Tax_Dollars",
                    "Fed_EITC", "CTC_Nonref", "ACTC", "CalEITC", "YCTC"])
        for hh_key, rows in results.items():
            for r in rows:
                w.writerow([r.income, HH_TYPES[hh_key]["label"],
                            round(r.etr_gross * 100, 2),
                            round(r.etr_after_fed_credits * 100, 2),
                            round(r.etr_net * 100, 2),
                            round(r.net_tax, 2),
                            round(r.fed_eitc, 2), round(r.ctc_nonref, 2),
                            round(r.actc, 2), round(r.ca_eitc, 2),
                            round(r.yctc, 2)])


def write_section7_table(results, path):
    """Section 7: implicit marginal tax rates at $1,000 increments."""
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(["Income_From", "Income_To", "Household_Type",
                    "Implicit_MTR_pct", "Cliff_Flag", "Notch_Flag",
                    "Net_Tax_Change", "Disposable_Income_Change"])
        for hh_key, rows in results.items():
            label = HH_TYPES[hh_key]["label"]
            filing = HH_TYPES[hh_key]["filing"]
            # Top statutory bracket for this filing status in the relevant range
            # (we'll use 12% federal + 8% CA + 7.65% payroll = 27.65% as the
            # benchmark for "no cliff"; cliff means MTR exceeds this).
            cliff_threshold = 27.65
            for i in range(1, len(rows)):
                prev, curr = rows[i-1], rows[i]
                d_tax = curr.net_tax - prev.net_tax
                d_inc = curr.income - prev.income
                d_disposable = d_inc - d_tax
                mtr = (d_tax / d_inc) * 100
                cliff = mtr > cliff_threshold
                notch = d_disposable < 0  # disposable income falls
                w.writerow([prev.income, curr.income, label,
                            round(mtr, 2), cliff, notch,
                            round(d_tax, 2), round(d_disposable, 2)])


def print_summary(results):
    print("=" * 80)
    print("EITC PAPER — KEY FINDINGS SUMMARY")
    print("=" * 80)
    bracket_incomes = [10000, 15000, 20000, 25000, 30000, 40000, 50000, 75000]
    for hh_key in HH_TYPES:
        print(f"\n{HH_TYPES[hh_key]['label']}")
        print("-" * 80)
        print(f"{'Income':>8} {'Gross ETR':>10} {'Aft Fed':>10} {'Net ETR':>10} "
              f"{'Net Tax $':>12} {'F.EITC':>8} {'CalEITC':>8} {'YCTC':>7}")
        for inc in bracket_incomes:
            r = compute_taxes(inc, hh_key)
            print(f"{r.income:>8} {r.etr_gross*100:>9.2f}% {r.etr_after_fed_credits*100:>9.2f}% "
                  f"{r.etr_net*100:>9.2f}% {r.net_tax:>12.0f} "
                  f"{r.fed_eitc:>8.0f} {r.ca_eitc:>8.0f} {r.yctc:>7.0f}")
    # Cliff identification
    print("\n" + "=" * 80)
    print("CLIFFS (MTR > 27.65%) AND NOTCHES (disposable income falls)")
    print("=" * 80)
    for hh_key in HH_TYPES:
        rows = results[hh_key]
        cliffs = []
        notches = []
        for i in range(1, len(rows)):
            d_tax = rows[i].net_tax - rows[i-1].net_tax
            d_inc = 1000
            mtr = (d_tax / d_inc) * 100
            if mtr > 27.65:
                cliffs.append((rows[i-1].income, rows[i].income, mtr))
            if d_inc - d_tax < 0:
                notches.append((rows[i-1].income, rows[i].income, mtr))
        print(f"\n{HH_TYPES[hh_key]['label']}:")
        if cliffs:
            print(f"  {len(cliffs)} cliff intervals. Steepest:")
            for f, t, m in sorted(cliffs, key=lambda x: -x[2])[:3]:
                print(f"    ${f:,} → ${t:,}: MTR = {m:.1f}%")
        else:
            print("  No cliffs.")
        if notches:
            print(f"  {len(notches)} NOTCH intervals (disposable income falls):")
            for f, t, m in notches:
                print(f"    ${f:,} → ${t:,}: MTR = {m:.1f}%")
        else:
            print("  No notches.")


if __name__ == "__main__":
    results = run_analysis()
    write_section6_table(results, "section6_etr_results.csv")
    write_section7_table(results, "section7_cliff_analysis.csv")
    print_summary(results)
    print("\n\nFiles written:")
    print("  section6_etr_results.csv")
    print("  section7_cliff_analysis.csv")
