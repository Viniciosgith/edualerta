import plotly.express as px
import streamlit as st
from modelo_ml import prever_risco_ml


def render(modelo_ia, metricas, matriz, df_importancias):
    st.title("IA Preditiva")
    st.caption("Simulador de risco em tempo real e validação estatística do modelo Random Forest.")

    aba_sim, aba_aud = st.tabs(["Simulador", "Validação do Modelo"])

    with aba_sim:
        col_ctrl, col_res = st.columns([3, 2])
        with col_ctrl:
            with st.container(border=True):
                st.markdown("**Parâmetros do Estudante**")
                nota = st.slider("Nota atual (0 a 10)", 0.0, 10.0, 6.2, 0.1)
                freq = st.slider("Frequência (%)", 40, 100, 78, 1)
                ativ = st.slider("Atividades entregues (%)", 0, 100, 35, 5)

                res = prever_risco_ml(modelo_ia, nota, freq, ativ)
                m1, m2 = st.columns(2)
                m1.metric("Probabilidade de Risco", f"{res['probabilidade']}%")
                m2.metric("Classificação", res["faixa"])

                if res["faixa"] == "ALTO RISCO":
                    st.error(res["recomendacao"])
                elif res["faixa"] == "RISCO MODERADO":
                    st.warning(res["recomendacao"])
                else:
                    st.success(res["recomendacao"])

        with col_res:
            with st.container(border=True):
                st.markdown("**Peso das Variáveis**")
                fig_imp = px.bar(
                    df_importancias, x="Peso (%)", y="Fator", orientation="h",
                    text="Peso (%)", template="plotly_white",
                )
                fig_imp.update_traces(marker_color="#2563eb")
                fig_imp.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), yaxis_title=None)
                st.plotly_chart(fig_imp, use_container_width=True)

    with aba_aud:
        m1, m2, m3, m4 = st.columns(4)
        m1.container(border=True).metric("Acurácia", f"{metricas['acuracia']}%")
        m2.container(border=True).metric("Precisão", f"{metricas['precisao']}%")
        m3.container(border=True).metric("Recall", f"{metricas['recall']}%")
        m4.container(border=True).metric("F1-Score", f"{metricas['f1']}%")

        col_cm, col_info = st.columns([2, 3])
        with col_cm:
            with st.container(border=True):
                fig_cm = px.imshow(
                    matriz, text_auto=True, color_continuous_scale="Blues",
                    x=["Prev. Normal", "Prev. Risco"], y=["Real Normal", "Real Risco"],
                )
                fig_cm.update_layout(height=300, coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig_cm, use_container_width=True)

        with col_info:
            with st.container(border=True):
                st.markdown("**Critérios de Governança**")
                st.write(
                    f"Treinamento estratificado 80/20 com **{metricas['amostras_treino']}** registros de treino "
                    f"e **{metricas['amostras_teste']}** de validação (150 árvores, profundidade máxima 8)."
                )
                st.write(
                    "O foco em **Recall elevado** reduz falsos negativos — evitando que estudantes em queda "
                    "de engajamento passem despercebidos antes do fechamento do período."
                )
