import streamlit as st
import plotly.express as px
from services import popular_dados_demo

CORES_RISCO = {
    "ALTO RISCO": "#dc2626",
    "RISCO MODERADO": "#d97706",
    "BAIXO RISCO": "#16a34a",
}


def render(df):
    col_titulo, col_filtro, col_export = st.columns([6, 1.4, 1.6], vertical_alignment="bottom")
    with col_titulo:
        st.title("Visão Geral")
        st.caption("Acompanhamento consolidado de desempenho acadêmico e alertas preditivos.")

    if df.empty:
        with st.container(border=True):
            st.subheader("Base de dados vazia")
            st.write("Carregue uma amostra demonstrativa ou importe uma planilha em **Gestão e Portais**.")
            if st.button("Carregar dados de demonstração", type="primary"):
                popular_dados_demo()
                st.rerun()
        return

    with col_filtro:
        with st.popover("Filtros", use_container_width=True):
            turmas = sorted(df["Turma"].unique())
            discs = sorted(df["Disciplina"].unique())
            turmas_sel = st.multiselect("Turma / Curso", turmas, default=turmas)
            disc_sel = st.multiselect("Disciplina", discs, default=discs)
            risco_sel = st.multiselect(
                "Classificação IA",
                ["ALTO RISCO", "RISCO MODERADO", "BAIXO RISCO"],
                default=["ALTO RISCO", "RISCO MODERADO", "BAIXO RISCO"],
            )

    df_f = df[
        df["Turma"].isin(turmas_sel)
        & df["Disciplina"].isin(disc_sel)
        & df["Classificação"].isin(risco_sel)
    ]

    colunas_tabela = ["Aluno", "Turma", "Disciplina", "Período", "Nota", "Frequência (%)", "Risco IA (%)", "Classificação"]

    with col_export:
        csv = df_f[colunas_tabela].to_csv(index=False, sep=";").encode("utf-8-sig")
        st.download_button("Exportar CSV", data=csv, file_name="edualerta_relatorio.csv", mime="text/csv", use_container_width=True)

    st.divider()

    if df_f.empty:
        st.info("Nenhum registro corresponde aos filtros selecionados.")
        return

    k1, k2, k3, k4 = st.columns(4)
    k1.container(border=True).metric("Estudantes", df_f["Matrícula"].nunique())
    k2.container(border=True).metric("Média Geral", f"{df_f['Nota'].mean():.1f}")
    k3.container(border=True).metric("Frequência Média", f"{df_f['Frequência (%)'].mean():.0f}%")
    k4.container(border=True).metric("Alertas de Alto Risco", int((df_f["Classificação"] == "ALTO RISCO").sum()))

    g1, g2 = st.columns([3, 2])
    with g1:
        with st.container(border=True):
            st.markdown("**Dispersão: Frequência × Nota**")
            fig_disp = px.scatter(
                df_f, x="Frequência (%)", y="Nota", color="Classificação",
                hover_data=["Aluno", "Turma", "Disciplina", "Atividades (%)"],
                color_discrete_map=CORES_RISCO, template="plotly_white",
            )
            fig_disp.update_traces(marker=dict(size=10, opacity=0.85))
            fig_disp.add_hline(y=7.0, line_dash="dot", line_color="#94a3b8")
            fig_disp.add_vline(x=75.0, line_dash="dot", line_color="#dc2626")
            fig_disp.update_layout(
                height=320, margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", y=1.12, title=None),
            )
            st.plotly_chart(fig_disp, use_container_width=True)

    with g2:
        with st.container(border=True):
            st.markdown("**Risco Médio por Disciplina**")
            gargalo = df_f.groupby("Disciplina", as_index=False)["Risco IA (%)"].mean().sort_values("Risco IA (%)")
            fig_bar = px.bar(
                gargalo, x="Risco IA (%)", y="Disciplina", orientation="h",
                template="plotly_white", color="Risco IA (%)",
                color_continuous_scale=["#16a34a", "#f59e0b", "#dc2626"],
            )
            fig_bar.update_layout(
                height=320, showlegend=False, coloraxis_showscale=False,
                margin=dict(l=0, r=0, t=10, b=0), yaxis_title=None,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    with st.container(border=True):
        st.markdown("**Prioridade de Acompanhamento**")
        st.dataframe(
            df_f[colunas_tabela].sort_values("Risco IA (%)", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Nota": st.column_config.NumberColumn(format="%.1f"),
                "Frequência (%)": st.column_config.ProgressColumn("Frequência", min_value=0, max_value=100, format="%.0f%%"),
                "Risco IA (%)": st.column_config.ProgressColumn("Risco IA", min_value=0, max_value=100, format="%.1f%%"),
            },
        )
