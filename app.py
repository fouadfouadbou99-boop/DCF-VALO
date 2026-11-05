import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import date
from io import BytesIO
import json

# Essayer d'importer le module de scénarios personnalisé
try:
    from scenario_module import run_scenarios
except ImportError:
    run_scenarios = None

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
    net_debt = st.number_input("Dette nette", value=100.0)
    shares = st.number_input("Nb actions (millions)", value=10.0)

    discount_mode = st.selectbox(
        "Méthode d'actualisation",
        ["Année pleine", "Mid-Year", "Durée résiduelle"]
    )
    
    fcff_method = st.selectbox(
        "Méthode FCFF",
        ["DCF Standard", "Excel alternative"]
    )
    
    first_bp_year = st.number_input(
        "Première année du BP",
        value=valuation_date.year,
        step=1
    )

# Calculs du WACC et Coût des Fonds Propres
cost_equity = rf + beta * mrp + sp
wacc = ((1 - debt_weight) * cost_equity) + (debt_weight * cost_debt * (1 - tax_rate))

# =====================
# BUSINESS PLAN
# =====================
st.header("1. Business Plan Inputs")

revenue0 = st.number_input("Chiffre d'Affaires de base (Année 0)", value=1000.0)

# Saisie dynamique des hypothèses annuelles sous forme de tableau compact
rows = []
for i in range(bp_years):
    st.markdown(f"**Année {i+1} ({first_bp_year + i})**")
    c1, c2, c3, c4, c5 = st.columns(5)
    rows.append({
        'Growth': c1.number_input('Croissance %', value=5.0, key=f'g{i}') / 100,
        'EBITDA': c2.number_input('Marge EBITDA %', value=25.0, key=f'e{i}') / 100,
        'D&A': c3.number_input('Amort. %', value=3.0, key=f'd{i}') / 100,
        'CAPEX': c4.number_input('CAPEX %', value=5.0, key=f'c{i}') / 100,
        'BFR': c5.number_input('BFR %', value=2.0, key=f'b{i}') / 100,
    })

# Calcul des projections financières
revenue = revenue0
bp = []

for i in range(bp_years):
    revenue *= (1 + rows[i]['Growth'])
    ebitda = revenue * rows[i]['EBITDA']
    dep = revenue * rows[i]['D&A']
    capex = revenue * rows[i]['CAPEX']
    bfr = revenue * rows[i]['BFR']
    ebit = ebitda - dep
    nopat = ebit * (1 - tax_rate)
    
    # Calcul de l'impôt théorique sur l'EBIT
    tax_on_ebit = ebit * tax_rate 

    if fcff_method == "Excel alternative":
        fcff = ebitda - tax_on_ebit - capex - bfr
    else:
        fcff = nopat + dep - capex - bfr
        
    bp.append([
        int(first_bp_year + i),
        round(revenue, 2),
        round(ebitda, 2),
        round(dep, 2),
        round(ebit, 2),
        round(nopat, 2),
        round(capex, 2),
        round(bfr, 2),
        round(fcff, 2)
    ])

# Génération du DataFrame
bp_df = pd.DataFrame(
    bp,
    columns=["Année", "CA", "EBITDA", "Amortissements", "EBIT", "NOPAT", "CAPEX", "Variation BFR", "FCFF"]
)

st.subheader("Tableau de flux projetés (BP)")
st.dataframe(bp_df.set_index("Année"), use_container_width=True)

# =====================
# ACTUALISATION & VALORISATION
# =====================
if discount_mode == 'Année pleine':
    periods = np.arange(1, bp_years + 1)
elif discount_mode == 'Mid-Year':
    periods = np.arange(1, bp_years + 1) - 0.5
else:
    # Calcul de la fraction d'année restante
    year_end = date(valuation_date.year, closing_month, 28 if closing_month == 2 else 30 if closing_month in [4, 6, 9, 11] else 31)
    if valuation_date > year_end:
        year_end = date(valuation_date.year + 1, closing_month, year_end.day)
    fraction = max(0.01, (year_end - valuation_date).days / 365)
    periods = np.array([fraction + i for i in range(bp_years)])

discounts = 1 / ((1 + wacc) ** periods)
fcffs = bp_df['FCFF'].values
pv_fcff = fcffs * discounts
pv_fcff_sum = pv_fcff.sum()

# Valeur Terminale (VT)
fcff_terminal = fcffs[-1] * (1 + terminal_growth)
tv = fcff_terminal / (wacc - terminal_growth) if wacc > terminal_growth else 0
pv_tv = tv * discounts[-1]

enterprise_value = pv_fcff_sum + pv_tv
equity_value = enterprise_value - net_debt
share_price = equity_value / shares if shares > 0 else 0

# =====================
# AFFICHAGE DES RESULTATS
# =====================
st.header("2. Résultats de la Valorisation")

col1, col2, col3, col4 = st.columns(4)
col1.metric('Enterprise Value (EV)', f'{enterprise_value:,.2f}')
col2.metric('Equity Value', f'{equity_value:,.2f}')
col3.metric('Prix Théorique / Action', f'{share_price:,.2f}')
col4.metric('WACC Calculé', f'{wacc * 100:.2f}%')

summary_df = pd.DataFrame({
    "Indicateur": [
        "Somme des FCFF Actualisés",
        "Valeur Terminale (générée)",
        "Valeur Terminale Actualisée",
        "Valeur d'Entreprise (EV)",
        "Dette Nette (-)",
        "Valeur des Fonds Propres",
        "Valeur par Action"
    ],
    "Valeur": [pv_fcff_sum, tv, pv_tv, enterprise_value, net_debt, equity_value, share_price]
})
st.dataframe(summary_df.set_index("Indicateur"), use_container_width=True)

st.subheader("Détail des calculs d'actualisation (DCF)")
dcf_df = pd.DataFrame({
    'Année': bp_df['Année'],
    'FCFF': fcffs,
    'Période d\'act.': periods,
    'Facteur d\'act.': discounts,
    'Flux Actualisé (PV)': pv_fcff
})
st.dataframe(dcf_df.set_index("Année"), use_container_width=True)

# =====================
# MATRICE DE SENSIBILITE
# =====================
st.header("3. Analyses Complémentaires")

st.subheader("Matrice de Sensibilité (Prix de l'action selon WACC et g)")
wacc_range = np.arange(max(0.04, wacc - 0.02), wacc + 0.021, 0.005)
g_range = np.arange(0.005, max(0.04, terminal_growth + 0.02), 0.005)

results = []
for w in wacc_range:
    for g in g_range:
        if w > g:
            w_discounts = 1 / ((1 + w) ** periods)
            w_pv_fcff = fcffs * w_discounts
            w_fcff_terminal = fcffs[-1] * (1 + g)
            w_tv = w_fcff_terminal / (w - g)
            w_pv_tv = w_tv * w_discounts[-1]
            
            tev = w_pv_fcff.sum() + w_pv_tv
            eq = tev - net_debt
            px_val = eq / shares if shares > 0 else 0
            
            results.append({
                "WACC (%)": round(w * 100, 2),
                "Croissance g (%)": round(g * 100, 2),
                "Prix": round(px_val, 2)
            })

sens_df = pd.DataFrame(results)
if not sens_df.empty:
    matrix_sens = sens_df.pivot(index="WACC (%)", columns="Croissance g (%)", values="Prix")
    st.dataframe(matrix_sens, use_container_width=True)

# Stress Tests
st.subheader("Stress Tests")
stress = pd.DataFrame({
    "Scénario": ["Optimiste (+15%)", "Cas de Base", "Dégradé (-15%)", "Crise (-30%)"],
    "Facteur": [1.15, 1.00, 0.85, 0.70]
})
stress["Prix Action"] = round(share_price * stress["Facteur"], 2)
st.dataframe(stress.set_index("Scénario"), use_container_width=True)

# =====================
# EXPORT EXCEL & JSON
# =====================
st.header("4. Sauvegarde et Exports")

buf = BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as writer:
    bp_df.to_excel(writer, sheet_name="BusinessPlan", index=False)
    dcf_df.to_excel(writer, sheet_name="DCF", index=False)
    if not sens_df.empty:
        matrix_sens.to_excel(writer, sheet_name="Sensibilite")
    stress.to_excel(writer, sheet_name="Stress", index=False)
buf.seek(0)

c_exp1, c_exp2 = st.columns(2)

c_exp1.download_button(
    label="📊 Télécharger le modèle Excel",
    data=buf.getvalue(),
    file_name=f"Corporate_Valuation_{company}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

save_data = {
    "company": company,
    "valuation_date": str(valuation_date),
    "closing_month": closing_month,
    "bp_years": bp_years,
    "first_bp_year": first_bp_year,
    "rf": rf, "beta": beta, "mrp": mrp, "sp": sp,
    "cost_debt": cost_debt, "tax_rate": tax_rate, "debt_weight": debt_weight,
    "terminal_growth": terminal_growth, "net_debt": net_debt, "shares": shares,
    "discount_mode": discount_mode, "fcff_method": fcff_method, "rows": rows
}

json_string = json.dumps(save_data, indent=4, ensure_ascii=False)
c_exp2.download_button(
    label="💾 Sauvegarder la session (JSON)",
    data=json_string,
    file_name=f"{company}.json",
    mime="application/json"
)

# Execution sûre du module externe de scénarios
if run_scenarios is not None:
    st.write("---")
    st.header("5. Module de Scénarios Avancés")
    try:
        run_scenarios(
            revenue0, rows, bp_years, tax_rate, terminal_growth, 
            wacc, periods, net_debt, shares, pv_fcff_sum, fcff_terminal
        )
    except Exception as e:
        st.error(f"Erreur lors du chargement des scénarios : {e}")
