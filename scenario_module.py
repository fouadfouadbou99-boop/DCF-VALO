# scenario_module.py

import streamlit as st
import plotly.graph_objects as go


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
):

    st.divider()

    st.header("📊 Module Scénarios")

    # =====================================================
    # HEATMAP WACC VS CROISSANCE TERMINALE
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
                    * (
                        1
                        / ((1 + w_test) ** periods[-1])
                    )
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
        xaxis_title="Croissance Terminale (%)",
        yaxis_title="WACC (%)"
    )

    st.plotly_chart(
        fig_g,
        use_container_width=True
    )

    st.markdown(
        f"""
La valeur par action est estimée sur la base d'un WACC central de
**{base_wacc:.2f}%** et d'un taux de croissance terminale central de
**{base_g:.2f}%**.

La matrice illustre l'impact combiné du coût du capital et de la croissance
à long terme. Une hausse du WACC entraîne mécaniquement une diminution de la
valeur d'entreprise tandis qu'une augmentation de la croissance terminale
accroît la valeur terminale et la valorisation de l'entreprise.
"""
    )
