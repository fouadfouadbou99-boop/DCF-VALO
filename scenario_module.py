# scenario_module.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


def run_scenarios(...)
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
):

    st.header("📊 Analyse de scénarios")

    # =====================================================
    # PARAMETRAGE DES SCENARIOS
    # =====================================================

    scenario_df = pd.DataFrame(
        {
            "Scénario": [
                "Optimiste",
                "Central",
                "Dégradé",
                "Stress",
            ],
            "Variation CA (%)": [
                10,
                0,
                -10,
                -20,
            ],
            "Variation EBITDA (pts)": [
                2,
                0,
                -2,
                -5,
            ],
            "Variation WACC (pts)": [
                -1,
                0,
                1,
                2,
            ],
            "Variation g (pts)": [
                0.50,
                0.00,
                -0.25,
                -0.50,
            ],
        }
    )

    scenario_df = st.data_editor(
        scenario_df,
        use_container_width=True,
        key="scenario_editor",
    )

    # =====================================================
    # CALCUL SCENARIOS
    # =====================================================

    scenario_results = []

    base_margin = rows[-1]["EBITDA"] * 100

    for _, scen in scenario_df.iterrows():

        growth_factor = (
            1
            + scen["Variation CA (%)"] / 100
        )

        margin_factor = (
            base_margin
            + scen["Variation EBITDA (pts)"]
        )

        scenario_wacc = (
            wacc
            + scen["Variation WACC (pts)"] / 100
        )

        scenario_g = (
            terminal_growth
            + scen["Variation g (pts)"] / 100
        )

        revenue_test = revenue0

        fcffs = []

        for i in range(bp_years):

            revenue_test *= (
                1 + rows[i]["Growth"]
            )

            revenue_test *= growth_factor

            ebitda_test = (
                revenue_test
                * margin_factor
                / 100
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

            fcffs.append(fcff_test)

        discounts = (
            1
            / (
                (1 + scenario_wacc)
                ** periods
            )
        )

        pv_fcff = (
            np.array(fcffs)
            * discounts
        ).sum()

        terminal_fcff = (
            fcffs[-1]
            * (1 + scenario_g)
        )

        tv = (
            terminal_fcff
            /
            (
                scenario_wacc
                - scenario_g
            )
        )

        pv_tv = (
            tv
            * discounts[-1]
        )

        ev = pv_fcff + pv_tv

        equity = (
            ev
            - net_debt
        )

        price = (
            equity
            / shares
        )

        scenario_results.append(
            [
                scen["Scénario"],
                round(ev, 2),
                round(equity, 2),
                round(price, 2),
            ]
        )

    results_df = pd.DataFrame(
        scenario_results,
        columns=[
            "Scénario",
            "EV",
            "Equity Value",
            "Valeur / Action",
        ],
    )

    st.subheader("Résultats")

    st.dataframe(
        results_df,
        use_container_width=True,
    )

    # =====================================================
    # GRAPHIQUE SCENARIOS
    # =====================================================

    fig = px.bar(
        results_df,
        x="Scénario",
        y="Valeur / Action",
        text="Valeur / Action",
        color="Valeur / Action",
    )

    fig.update_layout(
        title="Comparaison des scénarios"
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    # =====================================================
    # HEATMAP WACC / G
    # =====================================================

    st.subheader(
        "📈 Sensibilité WACC / Croissance Terminale"
    )

    base_g = terminal_growth * 100

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

    base_wacc = wacc * 100

    wacc_range = [
        round(base_wacc - 2, 2),
        round(base_wacc - 1.5, 2),
        round(base_wacc - 1, 2),
        round(base_wacc - 0.5, 2),
        round(base_wacc, 2),
        round(base_wacc + 0.5, 2),
        round(base_wacc + 1, 2),
        round(base_wacc + 1.5, 2),
        round(base_wacc + 2, 2),
    ]

    heatmap_g = []

    for w in wacc_range:

        row_values = []

        for g in g_range:

            if (w / 100) <= (g / 100):

                row_values.append(None)

            else:

                tv = (
                    fcff_terminal
                    /
                    (
                        (w / 100)
                        - (g / 100)
                    )
                )

                pv_tv = (
                    tv
                    * discounts[-1]
                )

                ev = (
                    pv_fcff_sum
                    + pv_tv
                )

                eq = (
                    ev
                    - net_debt
                )

                px_value = (
                    eq
                    / shares
                )

                row_values.append(
                    round(px_value, 0)
                )

        heatmap_g.append(
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
            texttemplate="%{text}",
        )
    )

    fig_g.update_layout(
        title="Valeur / Action",
        xaxis_title="Croissance Terminale",
        yaxis_title="WACC",
    )

    st.plotly_chart(
        fig_g,
        use_container_width=True,
    )

    # =====================================================
    # HEATMAP WACC / EBITDA
    # =====================================================

    st.subheader(
        "📊 Sensibilité WACC / EBITDA"
    )

    base_margin = (
        rows[-1]["EBITDA"]
        * 100
    )

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

            ev = (
                pv_fcff_sum
                * (
                    margin
                    / base_margin
                )
            )

            eq = (
                ev
                - net_debt
            )

            px_value = (
                eq
                / shares
            )

            row_values.append(
                round(px_value, 0)
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
            texttemplate="%{text}",
        )
    )

    fig_ebitda.update_layout(
        title="Valeur / Action",
        xaxis_title="Marge EBITDA",
        yaxis_title="WACC",
    )

    st.plotly_chart(
        fig_ebitda,
        use_container_width=True,
    )

    st.success(
        "Module Scénarios chargé avec succès."
    )
