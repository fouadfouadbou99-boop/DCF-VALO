import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from io import BytesIO
import json

st.set_page_config(page_title="Corporate Valuation Platform", layout="wide")
st.title("Corporate Valuation Platform")

# =====================
# PARAMETRES (SIDEBAR)
# =====================
with st.sidebar:
    st.header("Paramètres généraux")
    company = st.text_input("Société", "Ma Société")
    valuation_date = st.date_input("Date de valorisation", date.today())
    closing_month = st.selectbox("Mois de clôture", list(range(1, 13)), index=11)
    bp_years = st.slider("Durée du Business Plan", 3, 10, 5)
    first_bp_year = st.number_input("Première année du BP", value=2027, step=1)

    st.header("WACC")
    rf = st.number_input("Taux sans risque (%)", value=3.0) / 100
    beta = st.number_input("Beta", value=1.0)
    mrp = st.number_input("Prime de marché (%)", value=6.0) / 100
    sp = st.number_input("Prime spécifique (%)", value=1.0) / 100
    cost_debt = st.number_input("Coût de la dette (%)", value=5.0) / 100
    tax_rate = st.number_input("IS (%)", value=30.0) / 100
    debt_weight = st.number_input("Poids dette (%)", value=20.0) / 100

    st.header("Valorisation")
    terminal_growth = st.number_input("Croissance terminale (%)", value=2.0) / 100
    net_debt = st.number_input("Dette nette", value=1461.0)
    minorities = st.number_input("Intérêts minoritaires", value=275.0)
    shares = st.number_input("Nb actions (millions)", value=13.21)

    discount_mode = st.selectbox(
        "Méthode d'actualisation",
        ["Année pleine", "Mid-Year", "Durée résiduelle"]
    )

    fcff_method = st.selectbox(
        "Méthode FCFF",
        ["Excel", "DCF Standard"]
    )

# =====================
# CALCUL DU WACC
# =====================
equity_weight = 1 - debt_weight
cost_equity = rf + beta * mrp + sp
cost_debt_after_tax = cost_debt
wacc = (equity_weight * cost_equity) + (debt_weight * cost_debt_after_tax)

st.sidebar.markdown("---")
st.sidebar.write(f"**Coût des fonds propres : {cost_equity*100:.2f}%**")
st.sidebar.write(f"**Coût de la dette après IS : {cost_debt_after_tax*100:.2f}%**")
st.sidebar.write(f"**WACC : {wacc*100:.2f}%**")

# =====================
# BUSINESS PLAN & ANNEE NORMATIVE
# =====================
st.header("Business Plan")
revenue0 = st.number_input("CA année 0", value=2831.0)

rows = []
for i in range(bp_years):
    c1, c2, c3, c4, c5 = st.columns(5)
    rows.append({
        'Growth': c1.number_input(f'Croissance Y{i+1} %', value=5.0, key=f'g{i}') / 100,
        'EBITDA': c2.number_input(f'Marge EBITDA Y{i+1} %', value=25.0, key=f'e{i}') / 100,
        'D&A': c3.number_input(f'Amort. Y{i+1} %', value=4.10, key=f'd{i}') / 100,
        'CAPEX': c4.number_input(f'CAPEX Y{i+1} %', value=3.0, key=f'c{i}') / 100,
        'BFR': c5.number_input(f'BFR Y{i+1} %', value=1.5, key=f'b{i}') / 100,
    })

st.subheader("Hypothèses Année Normative (Valeur Terminale)")
use_custom_normative = st.checkbox(
    "Activer le calcul détaillé du flux normatif (recommandé pour alignement rapport)",
    value=True
)

if use_custom_normative:
    cn1, cn2, cn3, cn4, cn5 = st.columns(5)
    norm_growth = cn1.number_input("Croissance Normative %", value=terminal_growth * 100, disabled=True) / 100
    norm_ebitda_m = cn2.number_input("Marge EBITDA Norm. %", value=25.02) / 100
    norm_da_m = cn3.number_input("Amort. Norm. %", value=2.05) / 100
    norm_capex_m = cn4.number_input("CAPEX Norm. %", value=2.05) / 100
    norm_bfr_m = cn5.number_input("BFR Norm. %", value=0.52) / 100

revenue = revenue0
bp = []

for i in range(bp_years):
    revenue = revenue * (1 + rows[i]["Growth"])
    rev_calc = round(revenue) if fcff_method == "Excel" else revenue
    
    ebitda = rev_calc * rows[i]["EBITDA"]
    dep = rev_calc * rows[i]["D&A"]
    capex = rev_calc * rows[i]["CAPEX"]
    bfr = rev_calc * rows[i]["BFR"]

    if fcff_method == "Excel":
        ebitda = round(ebitda)
        dep = round(dep)
        capex = round(capex)
        bfr = round(bfr)

    ebit = ebitda - dep
    tax = round(ebit * tax_rate) if fcff_method == "Excel" else (ebit * tax_rate)
    nopat = ebit - tax

    if fcff_method == "Excel":
        fcff = ebitda - tax - capex - bfr
    else:
        fcff = round(nopat + dep - capex - bfr, 0)

    bp.append([
        str(first_bp_year + i),
        rev_calc,
        ebitda,
        dep,
        ebit,
        nopat,
        capex,
        bfr,
        fcff
    ])

if use_custom_normative:
    rev_norm = round(revenue * (1 + terminal_growth)) if fcff_method == "Excel" else revenue * (1 + terminal_growth)
    ebitda_norm = round(rev_norm * norm_ebitda_m) if fcff_method == "Excel" else rev_norm * norm_ebitda_m
    dep_norm = round(rev_norm * norm_da_m) if fcff_method == "Excel" else rev_norm * norm_da_m
    capex_norm = round(rev_norm * norm_capex_m) if fcff_method == "Excel" else rev_norm * norm_capex_m
    bfr_norm = round(rev_norm * norm_bfr_m) if fcff_method == "Excel" else rev_norm * norm_bfr_m
    
    ebit_norm = ebitda_norm - dep_norm
    tax_norm = round(ebit_norm * tax_rate) if fcff_method == "Excel" else ebit_norm * tax_rate
    nopat_norm = ebit_norm - tax_norm
    
    if fcff_method == "Excel":
        fcff_terminal = ebitda_norm - tax_norm - capex_norm - bfr_norm
    else:
        fcff_terminal = round(nopat_norm + dep_norm - capex_norm - bfr_norm, 0)
        
    bp.append([
        "Normatif",
        rev_norm,
        ebitda_norm,
        dep_norm,
        ebit_norm,
        nopat_norm,
        capex_norm,
        bfr_norm,
        fcff_terminal
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

# Séparation des années explicites du BP (hors ligne Normatif)
bp_explicit_df = bp_df[bp_df['Année'] != 'Normatif'].copy()

col_bp1, col_bp2 = st.columns([1.4, 1])

with col_bp1:
    st.dataframe(bp_df, use_container_width=True)

with col_bp2:
    fig_bp = go.Figure()
    fig_bp.add_trace(go.Bar(x=bp_explicit_df["Année"], y=bp_explicit_df["CA"], name="CA", marker_color="#1f77b4"))
    fig_bp.add_trace(go.Bar(x=bp_explicit_df["Année"], y=bp_explicit_df["EBITDA"], name="EBITDA", marker_color="#2ca02c"))
    fig_bp.add_trace(go.Scatter(x=bp_explicit_df["Année"], y=bp_explicit_df["FCFF"], name="FCFF", mode="lines+markers", line=dict(color="#ff7f0e", width=3)))
    fig_bp.update_layout(
        title="Trajectoire Financière (CA, EBITDA & FCFF)",
        barmode="group",
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_bp, use_container_width=True)

# =====================
# ACTUALISATION (DCF)
# =====================
if discount_mode == 'Année pleine':
    periods = np.arange(1, bp_years + 1)
elif discount_mode == 'Mid-Year':
    periods = np.arange(1, bp_years + 1) - 0.5
else:
    last_day = 28 if closing_month == 2 else 30 if closing_month in [4, 6, 9, 11] else 31
    year_end = date(valuation_date.year, closing_month, last_day)
    if valuation_date > year_end:
        year_end = date(valuation_date.year + 1, closing_month, last_day)
    fraction = max(0.01, (year_end - valuation_date).days / 365)
    periods = np.array([fraction + i for i in range(bp_years)])

discounts = 1 / ((1 + wacc) ** periods)

fcffs = bp_explicit_df['FCFF'].values
pv_fcff = fcffs * discounts
pv_fcff_sum = pv_fcff.sum()

if not use_custom_normative:
    fcff_terminal = fcffs[-1] * (1 + terminal_growth)

tv = fcff_terminal / (wacc - terminal_growth) if wacc > terminal_growth else 0
pv_tv = tv * discounts[-1]

enterprise_value = pv_fcff_sum + pv_tv
equity_value = enterprise_value - net_debt - minorities
share_price = equity_value / shares if shares > 0 else 0

# =====================
# RESULTATS & SYNTHESE
# =====================
st.header("Résultats de la Valorisation")
col1, col2, col3, col4 = st.columns(4)
col1.metric('Enterprise Value', f'{enterprise_value:,.0f}')
col2.metric('Equity Value', f'{equity_value:,.0f}')
col3.metric('Prix Action', f'{share_price:,.2f}')
col4.metric('WACC', f'{wacc*100:.2f}%')

col_res1, col_res2 = st.columns([1, 1.3])

with col_res1:
    summary_df = pd.DataFrame({
        "Indicateur": [
            "Somme FCFF Actualisés",
            "Valeur Terminale",
            "VT Actualisée",
            "Valeur d'Entreprise",
            "Dette Nette",
            "Intérêts Minoritaires",
            "Valeur des Fonds Propres",
            "Valeur par Action"
        ],
        "Valeur": [
            pv_fcff_sum,
            tv,
            pv_tv,
            enterprise_value,
            net_debt,
            minorities,
            equity_value,
            share_price
        ]
    })
    st.dataframe(summary_df, use_container_width=True)

with col_res2:
    fig_waterfall = go.Figure(go.Waterfall(
        name="Valorisation",
        orientation="v",
        measure=["relative", "relative", "total", "relative", "relative", "total"],
        x=["PV des FCFF", "PV Valeur Terminale", "Enterprise Value", "Dette Nette", "Minoritaires", "Equity Value"],
        textposition="outside",
        text=[f"{pv_fcff_sum:,.0f}", f"{pv_tv:,.0f}", f"{enterprise_value:,.0f}", f"{-net_debt:,.0f}", f"{-minorities:,.0f}", f"{equity_value:,.0f}"],
        y=[pv_fcff_sum, pv_tv, 0, -net_debt, -minorities, 0],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#2ca02c"}},
        decreasing={"marker": {"color": "#d62728"}},
        totals={"marker": {"color": "#1f77b4"}}
    ))
    fig_waterfall.update_layout(
        title="Pont de Valorisation (Enterprise Value vers Equity Value)",
        showlegend=False,
        height=360,
        margin=dict(l=20, r=20, t=40, b=20)
    )

# =====================
# SENSIBILITE (PIVOT & HEATMAP)
# =====================
st.header("Analyse de Sensibilité : WACC vs Croissance Terminale (g)")
results = []

w_range = np.arange(max(0.05, wacc - 0.02), wacc + 0.021, 0.005)
g_range = np.arange(0.01, 0.046, 0.005)

for w in w_range:
    for g in g_range:
        if w > g:
            tev = pv_fcff_sum + ((fcff_terminal / (w - g)) * discounts[-1])
            eq = tev - net_debt - minorities
            px_val = eq / shares if shares > 0 else 0
            results.append([round(w * 100, 2), round(g * 100, 2), round(px_val, 2)])
        else:
            results.append([round(w * 100, 2), round(g * 100, 2), np.nan])

sens = pd.DataFrame(results, columns=["WACC (%)", "g (%)", "Prix"])

# Création du tableau croisé dynamique (Pivot)
sens_pivot = sens.pivot(index="WACC (%)", columns="g (%)", values="Prix")

col_sens1, col_sens2 = st.columns([1, 1.2])

with col_sens1:
    st.subheader("Matrice des Prix par Action")
    st.dataframe(
        sens_pivot.style.format("{:.2f}", na_rep="-").background_gradient(cmap="RdYlGn", axis=None),
        use_container_width=True
    )

with col_sens2:
    st.subheader("Heatmap WACC vs Croissance (g)")
    fig_heatmap = px.imshow(
        sens_pivot,
        labels=dict(x="Croissance Terminale g (%)", y="WACC (%)", color="Prix Action"),
        x=[f"{col:.2f}%" for col in sens_pivot.columns],
        y=[f"{idx:.2f}%" for idx in sens_pivot.index],
        text_auto=".2f",
        color_continuous_scale="RdYlGn",
        aspect="auto"
    )
    fig_heatmap.update_layout(
        height=380,
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

# =====================
# STRESS TESTS
# =====================
st.subheader("Stress Tests")
stress = pd.DataFrame({
    "Scénario": ["Optimiste", "Base", "Dégradé", "Crise"],
    "Facteur": [1.15, 1.00, 0.85, 0.70]
})
stress["Prix Action"] = share_price * stress["Facteur"]
st.dataframe(stress, use_container_width=True)

# =====================
# EXPORTS (EXCEL & JSON)
# =====================
st.header("Exports")
col_exp1, col_exp2 = st.columns(2)

buf = BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as writer:
    bp_df.to_excel(writer, sheet_name="BusinessPlan", index=False)
    dcf_df.to_excel(writer, sheet_name="DCF", index=False)
    summary_df.to_excel(writer, sheet_name="Synthese", index=False)
    sens_pivot.to_excel(writer, sheet_name="Sensibilite_Pivot")
    stress.to_excel(writer, sheet_name="Stress", index=False)
buf.seek(0)

with col_exp1:
    st.download_button(
        label="Télécharger le modèle Excel (.xlsx)",
        data=buf,
        file_name=f"Valorisation_{company.replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

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
    "minorities": minorities,
    "shares": shares,
    "discount_mode": discount_mode,
    "fcff_method": fcff_method,
    "revenue0": revenue0,
    "bp_assumptions": rows
}

with col_exp2:
    st.download_button(
        label="Sauvegarder les paramètres (.json)",
        data=json.dumps(save_data, indent=4),
        file_name=f"Params_{company.replace(' ', '_')}.json",
        mime="application/json"
    )
