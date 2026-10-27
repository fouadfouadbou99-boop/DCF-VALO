import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import date
from io import BytesIO

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
    ebit = ebitda - dep
    nopat = ebit * (1-tax_rate)
    capex = revenue * rows[i]['CAPEX']
    bfr = revenue * rows[i]['BFR']
    fcff = nopat + dep - capex - bfr

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

st.subheader('DCF')

dcf_df = pd.DataFrame({
    'Année': bp_df['Année'],
    'FCFF': fcffs,
    'Période': periods,
    'Facteur': discounts,
    'PV FCFF': pv_fcff
})

st.dataframe(dcf_df, use_container_width=True)

fig = px.line(bp_df, x='Année', y=['CA','EBITDA','FCFF'])
st.plotly_chart(fig, use_container_width=True)

st.subheader('Sensibilité')
results=[]
for w in np.arange(max(0.05,wacc-0.02), wacc+0.021, 0.005):
    for g in np.arange(0.01,0.05,0.005):
        if w>g:
            tev = pv_fcff_sum + ((fcff_terminal/(w-g))*discounts[-1])
            eq = tev-net_debt
            results.append([round(w*100,2),round(g*100,2),eq/shares])

sens = pd.DataFrame(results, columns=['WACC','g','Prix'])
st.dataframe(sens, use_container_width=True)

st.subheader('Stress Tests')
stress = pd.DataFrame({
    'Scénario':['Optimiste','Base','Dégradé','Crise'],
    'Facteur':[1.15,1.0,0.85,0.70]
})
stress['Prix Action']=share_price*stress['Facteur']
st.dataframe(stress, use_container_width=True)

buf = BytesIO()
with pd.ExcelWriter(buf, engine='openpyxl') as writer:
    bp_df.to_excel(writer, sheet_name='BusinessPlan', index=False)
    dcf_df.to_excel(writer, sheet_name='DCF', index=False)
    sens.to_excel(writer, sheet_name='Sensibilite', index=False)
    stress.to_excel(writer, sheet_name='Stress', index=False)

buf.seek(0)
st.download_button('Télécharger Excel', buf.getvalue(), 'Corporate_Valuation.xlsx')
