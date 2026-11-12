import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import calendar

from datetime import date
from io import BytesIO
import json

# =====================================================
# CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Corporate Valuation Platform",
    layout="wide"
)

st.title("Corporate Valuation Platform")

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:

    st.header("Paramètres Généraux")

    company = st.text_input(
        "Société",
        "Ma Société"
    )

    valuation_date = st.date_input(
        "Date de valorisation",
        date.today()
    )

    closing_month = st.selectbox(
        "Mois de clôture",
        list(range(1, 13)),
        index=11
    )

    bp_years = st.slider(
        "Durée du BP",
        3,
        10,
        5
    )

    # -------------------------
    # WACC
    # -------------------------

    st.header("WACC")

    rf = st.number_input(
        "Taux sans risque (%)",
        value=3.0
    ) / 100

    beta = st.number_input(
        "Beta",
        value=1.0
    )

    mrp = st.number_input(
        "Prime de marché (%)",
        value=6.0
    ) / 100

    sp = st.number_input(
        "Prime spécifique (%)",
        value=1.0
    ) / 100

    cost_debt = st.number_input(
        "Coût de la dette (%)",
        value=5.0
    ) / 100

    tax_rate = st.number_input(
        "IS (%)",
        value=30.0
    ) / 100

    debt_weight = st.number_input(
        "Poids dette (%)",
        value=20.0
    ) / 100

    # -------------------------
    # Valorisation
    # -------------------------

    st.header("Valorisation")

    terminal_growth = st.number_input(
        "Croissance terminale (%)",
        value=2.0
    ) / 100

    net_debt = st.number_input(
        "Dette nette",
        value=100.0
    )

    minority_interest = st.number_input(
        "Intérêts minoritaires",
        value=0.0
    )

    financial_assets = st.number_input(
        "Participations financières",
        value=0.0
    )

    shares = st.number_input(
        "Nombre d'actions",
        value=10.0,
        min_value=0.0001
    )

    discount_mode = st.selectbox(
        "Méthode d'actualisation",
        [
            "Année pleine",
            "Mid-Year",
            "Durée résiduelle"
        ]
    )

    first_bp_year = st.number_input(
        "Première année du BP",
        value=date.today().year
    )

# =====================================================
# WACC
# =====================================================

cost_equity = rf + beta * mrp + sp

wacc = (
    (1 - debt_weight) * cost_equity
    + debt_weight * cost_debt * (1 - tax_rate)
)

if terminal_growth >= wacc:
    st.error(
        "La croissance terminale doit être inférieure au WACC."
    )
    st.stop()

# =====================================================
# BUSINESS PLAN
# =====================================================

st.header("1. Business Plan")

revenue0 = st.number_input(
    "CA Année 0",
    value=1000.0
)

initial_bfr = st.number_input(
    "BFR Initial",
    value=revenue0 * 0.02
)

rows = []

for i in range(bp_years):

    st.markdown(
        f"### Année {first_bp_year + i}"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    rows.append({
        "Growth":
            c1.number_input(
                "Croissance %",
                0.0,
                100.0,
                5.0,
                key=f"g{i}"
            ) / 100,

        "EBITDA":
            c2.number_input(
                "Marge EBITDA %",
                0.0,
                100.0,
                25.0,
                key=f"e{i}"
            ) / 100,

        "DA":
            c3.number_input(
                "Amort. %",
                0.0,
                100.0,
                3.0,
                key=f"d{i}"
            ) / 100,

        "CAPEX":
            c4.number_input(
                "CAPEX %",
                0.0,
                100.0,
                5.0,
                key=f"c{i}"
            ) / 100,

        "BFR":
            c5.number_input(
                "BFR %",
                0.0,
                100.0,
                2.0,
                key=f"b{i}"
            ) / 100
    })

# =====================================================
# PROJECTIONS
# =====================================================

revenue = revenue0

bp = []

bfr_previous = initial_bfr

for i in range(bp_years):

    revenue *= (
        1 + rows[i]["Growth"]
    )

    ebitda = revenue * rows[i]["EBITDA"]

    dep = revenue * rows[i]["DA"]

    capex = revenue * rows[i]["CAPEX"]

    bfr_level = revenue * rows[i]["BFR"]

    bfr_variation = (
        bfr_level - bfr_previous
    )

    ebit = ebitda - dep

    nopat = ebit * (
        1 - tax_rate
    )

    fcff = (
        nopat
        + dep
        - capex
        - bfr_variation
    )

    bp.append([
        first_bp_year + i,
        revenue,
        ebitda,
        dep,
        ebit,
        nopat,
        capex,
        bfr_variation,
        fcff
    ])

    bfr_previous = bfr_level

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

st.dataframe(
    bp_df,
    use_container_width=True
)

# =====================================================
# GRAPHIQUES
# =====================================================

fig_ca = px.line(
    bp_df,
    x="Année",
    y="CA",
    markers=True,
    title="Evolution du CA"
)

st.plotly_chart(
    fig_ca,
    use_container_width=True
)

fig_ebitda = px.line(
    bp_df,
    x="Année",
    y="EBITDA",
    markers=True,
    title="Evolution EBITDA"
)

st.plotly_chart(
    fig_ebitda,
    use_container_width=True
)

fig_fcff = px.bar(
    bp_df,
    x="Année",
    y="FCFF",
    title="Evolution FCFF"
)

st.plotly_chart(
    fig_fcff,
    use_container_width=True
)

# =====================================================
# ACTUALISATION
# =====================================================

if discount_mode == "Année pleine":

    periods = np.arange(
        1,
        bp_years + 1
    )

elif discount_mode == "Mid-Year":

    periods = (
        np.arange(bp_years)
        + 0.5
    )

else:

    days_in_month = calendar.monthrange(
        valuation_date.year,
        closing_month
    )[1]

    year_end = date(
        valuation_date.year,
        closing_month,
        days_in_month
    )

    if valuation_date > year_end:

        year_end = date()
            valuation
