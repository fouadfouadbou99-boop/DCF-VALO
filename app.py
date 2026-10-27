import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ---------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------

st.set_page_config(
    page_title="Corporate Valuation Platform",
    page_icon="📈",
    layout="wide"
)

# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------

st.sidebar.title("Corporate Valuation")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Paramètres",
        "Business Plan",
        "DCF",
        "Sensibilité",
        "Stress Tests",
        "Multiples",
        "Rapport Comité"
    ]
)

# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------

if "revenue" not in st.session_state:
    st.session_state.revenue = 100

if "growth" not in st.session_state:
    st.session_state.growth = 5

if "ebitda_margin" not in st.session_state:
    st.session_state.ebitda_margin = 20

if "tax" not in st.session_state:
    st.session_state.tax = 30

if "wacc" not in st.session_state:
    st.session_state.wacc = 10

if "g" not in st.session_state:
    st.session_state.g = 2

if "net_debt" not in st.session_state:
    st.session_state.net_debt = 20

if "shares" not in st.session_state:
    st.session_state.shares = 1

# ---------------------------------------------------
# FONCTIONS
# ---------------------------------------------------

def build_business_plan():

    revenue = st.session_state.revenue
    growth = st.session_state.growth / 100
    margin = st.session_state.ebitda_margin / 100
    tax_rate = st.session_state.tax / 100

    rows = []
    current = revenue

    for year in range(1, 6):

        current *= (1 + growth)

        ebitda = current * margin

        depreciation = current * 0.03

        ebit = ebitda - depreciation

        nopat = ebit * (1 - tax_rate)

        capex = current * 0.05

        nwc = current * 0.02

        fcff = nopat + depreciation - capex - nwc

        rows.append([
            year,
            current,
            ebitda,
            ebit,
            nopat,
            capex,
            nwc,
            fcff
        ])

    cols = [
        "Year",
        "Revenue",
        "EBITDA",
        "EBIT",
        "NOPAT",
        "CAPEX",
        "NWC",
        "FCFF"
    ]

    return pd.DataFrame(rows, columns=cols)

def dcf_valuation(df):

    fcffs = df["FCFF"].values

    wacc = st.session_state.wacc / 100
    g = st.session_state.g / 100

    pv_fcff = 0

    for i, fcff in enumerate(fcffs):
        pv_fcff += fcff / ((1 + wacc) ** (i + 0.5))

    terminal_value = (
        fcffs[-1] * (1 + g) /
        (wacc - g)
    )

    pv_tv = terminal_value / (
        (1 + wacc) ** (len(fcffs) - 0.5)
    )

    ev = pv_fcff + pv_tv

    equity = ev - st.session_state.net_debt

    value_per_share = equity / st.session_state.shares

    return {
        "EV": ev,
        "Equity": equity,
        "Price": value_per_share,
        "PV_FCFF": pv_fcff,
        "PV_TV": pv_tv
    }

# ---------------------------------------------------
# PARAMETRES
# ---------------------------------------------------

if page == "Paramètres":

    st.title("Paramètres")

    col1, col2 = st.columns(2)

    with col1:

        st.session_state.revenue = st.number_input(
            "CA Initial (MDH)",
            value=float(st.session_state.revenue)
        )

        st.session_state.growth = st.number_input(
            "Croissance (%)",
            value=float(st.session_state.growth)
        )

        st.session_state.ebitda_margin = st.number_input(
            "Marge EBITDA (%)",
            value=float(st.session_state.ebitda_margin)
        )

    with col2:

        st.session_state.tax = st.number_input(
            "IS (%)",
            value=float(st.session_state.tax)
        )

        st.session_state.wacc = st.number_input(
            "WACC (%)",
            value=float(st.session_state.wacc)
        )

        st.session_state.g = st.number_input(
            "Croissance terminale (%)",
            value=float(st.session_state.g)
        )

        st.session_state.net_debt = st.number_input(
            "Dette nette",
            value=float(st.session_state.net_debt)
        )

        st.session_state.shares = st.number_input(
            "Nb Actions",
            value=float(st.session_state.shares)
        )

# ---------------------------------------------------
# BUSINESS PLAN
# ---------------------------------------------------

elif page == "Business Plan":

    st.title("Business Plan")

    bp = build_business_plan()

    st.dataframe(bp, use_container_width=True)

# ---------------------------------------------------
# DCF
# ---------------------------------------------------

elif page == "DCF":

    st.title("Valorisation DCF")

    bp = build_business_plan()

    result = dcf_valuation(bp)

    c1, c2, c3 = st.columns(3)

    c1.metric("Enterprise Value", f"{result['EV']:,.1f}")
    c2.metric("Equity Value", f"{result['Equity']:,.1f}")
    c3.metric("Valeur / Action", f"{result['Price']:,.2f}")

# ---------------------------------------------------
# SENSIBILITE
# ---------------------------------------------------

elif page == "Sensibilité":

    st.title("Sensibilité WACC / g")

    bp = build_business_plan()

    waccs = np.arange(8,13,1)
    gs = np.arange(1,5,1)

    matrix = []

    for w in waccs:

        row=[]

        for g in gs:

            st.session_state.wacc = w
            st.session_state.g = g

            ev = dcf_valuation(bp)["EV"]

            row.append(round(ev,1))

        matrix.append(row)

    sensi = pd.DataFrame(
        matrix,
        index=waccs,
        columns=gs
    )

    fig = px.imshow(
        sensi,
        text_auto=True,
        color_continuous_scale="RdYlGn"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# ---------------------------------------------------
# STRESS TESTS
# ---------------------------------------------------

elif page == "Stress Tests":

    st.title("Stress Tests")

    scenarios = {
        "Optimiste":1.10,
        "Base":1.00,
        "Dégradé":0.90,
        "Crise":0.75
    }

    results=[]

    for s,factor in scenarios.items():

        revenue = st.session_state.revenue

        st.session_state.revenue = revenue*factor

        bp = build_business_plan()

        ev = dcf_valuation(bp)["EV"]

        results.append([s, ev])

        st.session_state.revenue = revenue

    df = pd.DataFrame(
        results,
        columns=["Scenario","EV"]
    )

    st.dataframe(df)

# ---------------------------------------------------
# MULTIPLES
# ---------------------------------------------------

elif page == "Multiples":

    st.title("Valorisation par Multiples")

    ebitda = st.number_input(
        "EBITDA",
        value=20.0
    )

    ev_multiple = st.number_input(
        "EV/EBITDA",
        value=8.0
    )

    ev = ebitda * ev_multiple

    st.metric(
        "Valeur Entreprise",
        f"{ev:,.1f}"
    )

# ---------------------------------------------------
# DASHBOARD
# ---------------------------------------------------

elif page == "Dashboard":

    bp = build_business_plan()
    result = dcf_valuation(bp)

    st.title("Dashboard Exécutif")

    c1,c2,c3,c4 = st.columns(4)

    c1.metric("EV", f"{result['EV']:,.1f}")
    c2.metric("Equity", f"{result['Equity']:,.1f}")
    c3.metric("Prix", f"{result['Price']:,.2f}")
    c4.metric("WACC", f"{st.session_state.wacc:.1f}%")

    fig = px.bar(
        bp,
        x="Year",
        y="FCFF",
        title="FCFF"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# ---------------------------------------------------
# RAPPORT
# ---------------------------------------------------

elif page == "Rapport Comité":

    bp = build_business_plan()
    result = dcf_valuation(bp)

    st.title("Rapport Comité")

    st.markdown(
        f"""
### Synthèse

- Enterprise Value : {result['EV']:,.1f} MDH
- Equity Value : {result['Equity']:,.1f} MDH
- Valeur par action : {result['Price']:,.2f}
- WACC : {st.session_state.wacc:.1f}%
- Croissance terminale : {st.session_state.g:.1f}%

### Conclusion

La société présente une valeur d'entreprise estimée à
{result['EV']:,.1f} MDH selon la méthode DCF.
"""
    )
