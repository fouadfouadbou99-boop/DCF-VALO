import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import date
from io import BytesIO
import json
import plotly.graph_objects as go
from scenario_module import run_scenarios

st.set_page_config(page_title="Corporate Valuation Platform", layout="wide")

st.title("Corporate Valuation Platform")

# =====================
# PARAMETRES
# =====================
with st.sidebar:
    st.header("Paramètres généraux")
    company = st.text_input("Société", "Ma Société")
    valuation_date = st.date_input("Date de valorisation", date.today())
    closing_month = st.selectbox("Mois de clôture", list(range(1,13)), index=11)
    bp_years = st.slider("Durée du Business Plan", 3, 10, 5)

    st.header("WACC")
    rf = st.number_input("Taux sans risque (%)", value=3.0)/100
    beta = st.number_input("Beta", value=1.0)
    mrp = st.number_input("Prime de marché (%)", value=6.0)/100
    sp = st.number_input("Prime spécifique (%)", value=1.0)/100
    cost_debt = st.number_input("Coût de la dette (%)", value=5.0)/100
    tax_rate = st.number_input("IS (%)", value=30.0)/100

    debt_weight = st.number_input("Poids dette (%)", value=20.0)/100

    st.header("Valorisation")
    terminal_growth = st.number_input("Croissance terminale (%)", value=2.0)/100
    net_debt = st.number_input("Dette nette", value=100.0)
    shares = st.number_input("Nb actions (millions)", value=10.0)

    discount_mode = st.selectbox(
        "Méthode d'actualisation",
        ["Année pleine", "Mid-Year", "Durée résiduelle"]
    )
fcff_method = st.selectbox(
    "Méthode FCFF",
    [
        "Excel",
        "DCF Standard"
    ]
)
cost_equity = rf + beta * mrp + sp
wacc = ((1 - debt_weight) * cost_equity) + (debt_weight * cost_debt * (1-tax_rate))
first_bp_year = st.number_input(
    "Première année du BP",
    value=2026,
    step=1
)
# =====================
# BUSINESS PLAN
# =====================
st.header("Business Plan")

revenue0 = st.number_input("CA année 0", value=1000.0)

rows = []
for i in range(bp_years):
    c1,c2,c3,c4,c5 = st.columns(5)
    rows.append({
        'Growth': c1.number_input(f'Croissance Y{i+1} %', value=5.0, key=f'g{i}')/100,
        'EBITDA': c2.number_input(f'Marge EBITDA Y{i+1} %', value=25.0, key=f'e{i}')/100,
        'D&A': c3.number_input(f'Amort. Y{i+1} %', value=3.0, key=f'd{i}')/100,
        'CAPEX': c4.number_input(f'CAPEX Y{i+1} %', value=5.0, key=f'c{i}')/100,
        'BFR': c5.number_input(f'BFR Y{i+1} %', value=2.0, key=f'b{i}')/100,
    })

calendar_year = valuation_date.year
revenue = revenue0
bp=[]

for i in range(bp_years):

    revenue *= (1 + rows[i]['Growth'])

    ebitda = revenue * rows[i]['EBITDA']

    dep = revenue * rows[i]['D&A']

    capex = revenue * rows[i]['CAPEX']

    bfr = revenue * rows[i]['BFR']

    ebit = ebitda - dep

    nopat = ebit * (1 - tax_rate)

    tax = ebitda * tax_rate

    if fcff_method == "Excel":

        fcff = (
            ebitda
            - tax
            - capex
            - bfr
        )

    else:

        fcff = (
            nopat
            + dep
            - capex
            - bfr
        )
    fcff = round(fcff, 0)
    bp.append([
    first_bp_year + i,
    revenue,
    ebitda,
    dep,
    ebit,
    nopat,
    capex,
    bfr,
    fcff
])
    bp_df = pd.DataFrame(
    bp,
    columns=[
        "Année",
        "CA",
        "EBITDA",
        "Amortissements",
        "EBIT",
        "NOPAT",
        "CAPEX",
        "Variation BFR",
        "FCFF"
    ]
)
st.write(bp_df.head())
st.dataframe(bp_df, use_container_width=True)

# =====================
# ACTUALISATION
# =====================
if discount_mode == 'Année pleine':
    periods = np.arange(1, bp_years+1)
elif discount_mode == 'Mid-Year':
    periods = np.arange(1, bp_years+1)-0.5
else:
    year_end = date(valuation_date.year, closing_month, 28 if closing_month==2 else 30 if closing_month in [4,6,9,11] else 31)
    if valuation_date > year_end:
        year_end = date(valuation_date.year+1, closing_month, year_end.day)
    fraction = max(0.01,(year_end-valuation_date).days/365)
    periods = np.array([fraction+i for i in range(bp_years)])

discounts = 1/((1+wacc)**periods)

fcffs = bp_df['FCFF'].values
pv_fcff = fcffs * discounts
pv_fcff_sum = pv_fcff.sum()

fcff_terminal = fcffs[-1]*(1+terminal_growth)
tv = fcff_terminal/(wacc-terminal_growth) if wacc>terminal_growth else 0
pv_tv = tv*discounts[-1]

enterprise_value = pv_fcff_sum + pv_tv
equity_value = enterprise_value - net_debt
share_price = equity_value / shares if shares>0 else 0

# =====================
# RESULTATS
# =====================
col1,col2,col3,col4 = st.columns(4)
col1.metric('Enterprise Value', f'{enterprise_value:,.0f}')
col2.metric('Equity Value', f'{equity_value:,.0f}')
col3.metric('Prix Action', f'{share_price:,.2f}')
col4.metric('WACC', f'{wacc*100:.2f}%')
summary_df = pd.DataFrame({
    "Indicateur": [
        "Somme FCFA",
        "Valeur Terminale",
        "VT Actualisée",
        "Valeur d'Entreprise",
        "Dette Nette",
        "Valeur des Fonds Propres",
        "Valeur par Action"
    ],
    "Valeur": [
        pv_fcff_sum,
        tv,
        pv_tv,
        enterprise_value,
        net_debt,
        equity_value,
        share_price
    ]
})

st.dataframe(
    summary_df,
    use_container_width=True
)

st.subheader('DCF')

dcf_df = pd.DataFrame({
    'Année': bp_df['Année'],
    'FCFF': fcffs,
    'Période': periods,
    'Facteur': discounts,
    'PV FCFF': pv_fcff
})
st.subheader("Sensibilité")

results = []

for w in np.arange(
    max(0.05, wacc - 0.02),
    wacc + 0.021,
    0.005
):

    for g in np.arange(
        0.01,
        0.05,
        0.005
    ):

        if w > g:

            tev = (
                pv_fcff_sum
                + ((fcff_terminal / (w - g))
                * discounts[-1])
            )

            eq = tev - net_debt

            px = eq / shares

            results.append([
                round(w*100,2),
                round(g*100,2),
                round(px,2)
            ])

sens = pd.DataFrame(
    results,
    columns=[
        "WACC",
        "g",
        "Prix"
    ]
)

st.dataframe(
    sens,
    use_container_width=True
)
st.subheader("Stress Tests")

stress = pd.DataFrame({
    "Scénario": [
        "Optimiste",
        "Base",
        "Dégradé",
        "Crise"
    ],
    "Facteur": [
        1.15,
        1.00,
        0.85,
        0.70
    ]
})

stress["Prix Action"] = (
    share_price
    * stress["Facteur"]
)

st.dataframe(
    stress,
    use_container_width=True
)
buf = BytesIO()

with pd.ExcelWriter(
    buf,
    engine="openpyxl"
) as writer:

    if 'bp_df' in locals():
        bp_df.to_excel(
            writer,
            sheet_name="BusinessPlan",
            index=False
        )

    if 'dcf_df' in locals():
        dcf_df.to_excel(
            writer,
            sheet_name="DCF",
            index=False
        )

    if 'sens' in locals():
        sens.to_excel(
            writer,
            sheet_name="Sensibilite",
            index=False
        )

    if 'stress' in locals():
        stress.to_excel(
            writer,
            sheet_name="Stress",
            index=False
        )

buf.seek(0)
st.subheader("🔥 Heatmap Stress Tests")
growth_shocks = [-10, -5, 0, 5, 10]

wacc_shocks = [-1, 0, 1, 2]

heatmap_values = []

for wacc_delta in wacc_shocks:

    row_values = []

    for growth_delta in growth_shocks:

        stressed_growth = (
            terminal_growth +
            growth_delta / 100
        )

        stressed_wacc = (
            wacc +
            wacc_delta / 100
        )

        if stressed_wacc <= stressed_growth:

            row_values.append(np.nan)

        else:

            stressed_tv = (
                fcff_terminal
                /
                (
                    stressed_wacc
                    - stressed_growth
                )
            )

            stressed_pv_tv = (
                stressed_tv
                * discounts[-1]
            )

            stressed_ev = (
                pv_fcff_sum
                + stressed_pv_tv
            )

            stressed_eq = (
                stressed_ev
                - net_debt
            )

            stressed_price = (
                stressed_eq
                / shares
            )

            row_values.append(
                round(
                    stressed_price,
                    2
                )
            )
st.subheader("📈 Sensibilité DCF : WACC vs Croissance Terminale")

base_g = terminal_growth * 100
base_wacc = wacc * 100

g_range = [
    round(base_g - 1.00, 2),
    round(base_g - 0.75, 2),
    round(base_g - 0.50, 2),
    round(base_g - 0.25, 2),
    round(base_g, 2),
    round(base_g + 0.25, 2),
    round(base_g + 0.50, 2),
    round(base_g + 0.75, 2),
    round(base_g + 1.00, 2)
]

wacc_range = [
    round(base_wacc - 2.00, 2),
    round(base_wacc - 1.50, 2),
    round(base_wacc - 1.00, 2),
    round(base_wacc - 0.50, 2),
    round(base_wacc, 2),
    round(base_wacc + 0.50, 2),
    round(base_wacc + 1.00, 2),
    round(base_wacc + 1.50, 2),
    round(base_wacc + 2.00, 2)
]

heatmap_g = []

for w in wacc_range:

    row_values = []

    for margin in ebitda_range:

        revenue_test = revenue0

        fcffs_test = []

        for i in range(bp_years):

            revenue_test *= (
                1 + rows[i]["Growth"]
            )

            ebitda_test = (
                revenue_test
                * (margin / 100)
            )

            tax_test = (
                ebitda_test
                * tax_rate
            )

            capex_test = (
                revenue_test
                * rows[i]["CAPEX"]
            )

            bfr_test = (
                revenue_test
                * rows[i]["BFR"]
            )

            fcff_test = (
                ebitda_test
                - tax_test
                - capex_test
                - bfr_test
            )

            fcffs_test.append(
                fcff_test
            )

        discounts_test = (
            1
            / (
                (1 + w/100)
                ** periods
            )
        )

        pv_fcff_test = (
            np.array(fcffs_test)
            * discounts_test
        ).sum()

        terminal_fcff_test = (
            fcffs_test[-1]
            * (1 + terminal_growth)
        )

        tv_test = (
            terminal_fcff_test
            /
            (
                (w/100)
                - terminal_growth
            )
        )

        pv_tv_test = (
            tv_test
            * discounts_test[-1]
        )

        ev_test = (
            pv_fcff_test
            + pv_tv_test
        )

        eq_test = (
            ev_test
            - net_debt
        )

        px_value = (
            eq_test
            / shares
        )

        row_values.append(
            round(px_value, 0)
        )

    heatmap_ebitda.append(
        row_values
    )


    heatmap_g.append(row_values)

fig_g = go.Figure(
    data=go.Heatmap(
        z=heatmap_g,
        x=[f"{x:.2f}%" for x in g_range],
        y=[f"{x:.2f}%" for x in wacc_range],
        colorscale="RdYlGn",
        reversescale=True,
        text=heatmap_g,
        texttemplate="%{text}"
    )
)

fig_g.update_layout(
    title="Valeur par Action : WACC vs Croissance Terminale",
    xaxis_title="Croissance Terminale",
    yaxis_title="WACC"
)

st.plotly_chart(
    fig_g,
    use_container_width=True
)
st.subheader("📊 Sensibilité DCF : WACC vs Marge EBITDA")

base_ebitda = rows[-1]["EBITDA"] * 100

ebitda_range = [
    round(base_ebitda - 3, 2),
    round(base_ebitda - 2, 2),
    round(base_ebitda - 1, 2),
    round(base_ebitda, 2),
    round(base_ebitda + 1, 2),
    round(base_ebitda + 2, 2),
    round(base_ebitda + 3, 2)
]

heatmap_ebitda = []

for w in wacc_range:

    row_values = []

    for margin in ebitda_range:

        revenue_test = revenue0

        fcffs_test = []

        for i in range(bp_years):

            revenue_test *= (
                1 + rows[i]["Growth"]
            )

            ebitda_test = (
                revenue_test
                * (margin / 100)
            )

            tax_test = (
                ebitda_test
                * tax_rate
            )

            capex_test = (
                revenue_test
                * rows[i]["CAPEX"]
            )

            bfr_test = (
                revenue_test
                * rows[i]["BFR"]
            )

            fcff_test = (
                ebitda_test
                - tax_test
                - capex_test
                - bfr_test
            )

            fcffs_test.append(fcff_test)

        discounts_test = (
            1
            / ((1 + w/100) ** periods)
        )

        pv_fcff_test = (
            np.array(fcffs_test)
            * discounts_test
        ).sum()

        terminal_fcff_test = (
            fcffs_test[-1]
            * (1 + terminal_growth)
        )

        tv_test = (
            terminal_fcff_test
            /
            (
                (w/100)
                - terminal_growth
            )
        )

        pv_tv_test = (
            tv_test
            * discounts_test[-1]
        )

        ev_test = (
            pv_fcff_test
            + pv_tv_test
        )

        eq_test = (
            ev_test
            - net_debt
        )

        price_test = (
            eq_test
            / shares
        )

        row_values.append(
            round(price_test, 0)
        )

    heatmap_ebitda.append(row_values)

fig_ebitda = go.Figure(
    data=go.Heatmap(
        z=heatmap_ebitda,
        x=[f"{x:.2f}%" for x in ebitda_range],
        y=[f"{x:.2f}%" for x in wacc_range],
        colorscale="RdYlGn",
        reversescale=True,
        text=heatmap_ebitda,
        texttemplate="%{text}"
    )
)

fig_ebitda.update_layout(
    title="Valeur par Action : WACC vs Marge EBITDA",
    xaxis_title="Marge EBITDA",
    yaxis_title="WACC"
)

st.plotly_chart(
    fig_ebitda,
    use_container_width=True
)




# =====================
# SAUVEGARDE JSON
# =====================

save_data = {
    "company": company,
    "valuation_date": str(valuation_date),
    "closing_month": closing_month,
    "bp_years": bp_years,
    "first_bp_year": first_bp_year,
    "rf": rf,
    "beta": beta,
    "mrp": mrp,
    "sp": sp,
    "cost_debt": cost_debt,
    "tax_rate": tax_rate,
    "debt_weight": debt_weight,
    "terminal_growth": terminal_growth,
    "net_debt": net_debt,
    "shares": shares,
    "discount_mode": discount_mode,
    "fcff_method": fcff_method,
    "rows": rows
}
st.download_button('Télécharger Excel', buf.getvalue(), 'Corporate_Valuation.xlsx')
json_string = json.dumps(
    save_data,
    indent=4,
    ensure_ascii=False
)

st.download_button(
    label="💾 Sauvegarder dossier JSON",
    data=json_string,
    file_name=f"{company}.json",
    mime="application/json"
)
run_scenarios(
    revenue0,
    rows,
    bp_years,
    tax_rate,
    terminal_growth,
    wacc,
    periods,
    net_debt,
    shares,
    pv_fcff_sum,
    fcff_terminal
)


