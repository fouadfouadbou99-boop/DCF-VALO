a# scenario_module.py

import streamlit as st
import numpy as np
import plotly.graph_objects as go
def run_scenarios(
    def run_scenarios(
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
    fcff_terminal,
    share_price
):

    st.divider()

    st.header("📊 Module Scénarios")

    # =====================================================
    # HEATMAP 1
    # WACC VS CROISSANCE TERMINALE
    # =====================================================

    st.subheader(
        "📈 Sensibilité DCF : WACC vs Croissance Terminale"
    )

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
        round(base_g + 1.00, 2),
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
        round(base_wacc + 2.00, 2),
    ]

    heatmap_g = []
for w in wacc_range:

    row_values = []

    for g in g_range:

        w_test = w / 100
        g_test = g / 100

        if w_test <= g_test:

            row_values.append(None)

        else:

            tv_test = (
                fcff_terminal
                / (w_test - g_test)
            )

            pv_tv_test = (
                tv_test
                * (1 / ((1 + w_test) ** periods[-1]))
            )

            ev_test = (
                pv_fcff_sum
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

    heatmap_g.append(row_values)  
    heatmap_ebitda = []

for w in wacc_range:

    row_values = []

    for margin in ebitda_range:

        ebitda_factor = (
            margin / base_margin
        )

        wacc_factor = (
            wacc / (w / 100)
        )

        price_test = (
            share_price
            * ebitda_factor
            * wacc_factor
        )

        row_values.append(
            round(price_test, 0)
        )

    heatmap_ebitda.append(
        row_values
    )

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
        title="Valeur par Action",
        xaxis_title="Croissance Terminale",
        yaxis_title="WACC"
    )

    st.plotly_chart(
        fig_g,
        use_container_width=True
    )

    st.markdown(
        """
La matrice présente l'impact combiné du coût moyen pondéré du capital (WACC)
et du taux de croissance terminale sur la valeur par action. Une hausse du
taux de croissance terminale entraîne une augmentation de la valeur terminale
et donc de la valorisation de l'entreprise. À l'inverse, un relèvement du
WACC réduit la valeur actuelle des flux futurs et diminue la valorisation.
Cette analyse permet d'encadrer la valeur obtenue dans le scénario central
et d'apprécier la sensibilité du DCF aux hypothèses de long terme.
"""
    )

    # =====================================================
    # HEATMAP 2
    # WACC VS EBITDA
    # =====================================================

    st.subheader(
        "📊 Sensibilité DCF : WACC vs Marge EBITDA"
    )

    base_margin = rows[-1]["EBITDA"] * 100

    ebitda_range = [
        round(base_margin - 3, 2),
        round(base_margin - 2, 2),
        round(base_margin - 1, 2),
        round(base_margin, 2),
        round(base_margin + 1, 2),
        round(base_margin + 2, 2),
        round(base_margin + 3, 2),
    ]

    heatmap_ebitda = []
    for w in wacc_range:

        row_values = []

    for margin in ebitda_range:

        price_test = (
            (
                pv_fcff_sum
                * (margin / base_margin)
            )
            /
            ((w / 100) / wacc)
        )

        row_values.append(
            round(price_test, 0)
        )

    heatmap_ebitda.append(
        row_values
    )

    

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
        title="Valeur par Action",
        xaxis_title="Marge EBITDA",
        yaxis_title="WACC"
    )

    st.plotly_chart(
        fig_ebitda,
        use_container_width=True
    )

    st.markdown(
        """
Cette matrice illustre l'incidence de la marge EBITDA sur la valeur par action.
Une amélioration de la rentabilité opérationnelle se traduit mécaniquement par
une augmentation de la génération de flux de trésorerie et donc de la valeur
de l'entreprise. La zone centrale correspond aux hypothèses opérationnelles
retenues dans le scénario de référence et permet d'apprécier l'impact d'une
amélioration ou d'une dégradation de la rentabilité.
"""
    )
