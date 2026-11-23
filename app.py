import pandas as pd
import plotly.express as px
import streamlit as st
from src.database import SessionLocal, Aluno, LogAlerta, init_db, popular_base_inicial
from src.ml_engine import treinar_pipeline, diagnosticar_aluno
from src.ai_agent import AgenteRetencaoIA

st.set_page_config(page_title="Sentinela Acadêmico | ML + Agente IA", layout="wide")


@st.cache_resource
def bootstrap():
    init_db()
    popular_base_inicial()
    pipeline, metricas = treinar_pipeline()
    return pipeline, metricas, AgenteRetencaoIA()


pipeline, metricas, agente = bootstrap()


def carregar_alunos_com_diagnostico():
    with SessionLocal() as db:
        alunos = db.query(Aluno).all()
        linhas = []
        for a in alunos:
            dados = {
                "id": a.id,
                "matricula": a.matricula,
                "nome": a.nome,
                "curso": a.curso,
                "semestre": a.semestre,
                "email_aluno": a.email_aluno,
                "media_notas": a.media_notas,
                "frequencia_pct": a.frequencia_pct,
                "acessos_ava_semana": a.acessos_ava_semana,
                "reprovacoes": a.reprovacoes,
                "dias_atraso_mensalidade": a.dias_atraso_mensalidade,
                "satisfacao_curso": a.satisfacao_curso,
            }
            res = diagnosticar_aluno(pipeline, dados)
            dados.update({
                "diagnostico": res["diagnostico"],
                "probabilidade": res["probabilidade"],
                "fatores": " | ".join(res["fatores"]),
                "resultado_ml": res,
            })
            linhas.append(dados)
        return linhas


st.title("Sentinela Acadêmico — Prevenção de Evasão com ML + Agente IA")
st.caption(
    f"Modelo Random Forest Multiclasse · Acurácia: {metricas['acuracia']}% · "
    f"F1-Macro: {metricas['f1_macro']}%"
)

aba_radar, aba_agente, aba_sim = st.tabs([
    "Radar de Risco", "Agente de IA & Alertas", "Cadastrar / Simular Aluno"
])

registros = carregar_alunos_com_diagnostico()
df = pd.DataFrame(registros)

with aba_radar:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de Alunos", len(df))
    c2.metric("Risco de Evasão", int((df["diagnostico"] == "Risco de Evasão").sum()))
    c3.metric("Risco de Trancamento", int((df["diagnostico"] == "Risco de Trancamento").sum()))
    c4.metric("Risco de Mudança", int((df["diagnostico"] == "Risco de Mudança de Curso").sum()))

    col_g, col_t = st.columns([2, 3])
    with col_g:
        contagem = df["diagnostico"].value_counts().reset_index()
        contagem.columns = ["Diagnóstico", "Quantidade"]
        fig = px.bar(
            contagem, x="Diagnóstico", y="Quantidade", color="Diagnóstico",
            color_discrete_map={
                "Permanência": "#16a34a",
                "Risco de Mudança de Curso": "#2563eb",
                "Risco de Trancamento": "#d97706",
                "Risco de Evasão": "#dc2626",
            },
            template="plotly_white",
        )
        fig.update_layout(showlegend=False, height=340, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_t:
        st.dataframe(
            df[["nome", "curso", "diagnostico", "probabilidade", "fatores"]],
            use_container_width=True,
            hide_index=True,
        )

with aba_agente:
    st.subheader("Central de Orquestração do Agente de IA")
    mapa_alunos = {f"{r['nome']} — {r['diagnostico']} ({r['probabilidade']}%)": r for r in registros}
    sel = st.selectbox("Selecione o estudante para o agente analisar", list(mapa_alunos.keys()))
    aluno_sel = mapa_alunos[sel]

    pacote = agente.gerar_alertas(aluno_sel, aluno_sel["resultado_ml"])

    st.info(
        f"**Prioridade:** {pacote['prioridade']}  |  "
        f"**Setor:** {pacote['setor']}  |  "
        f"**Ação:** {pacote['acao']}"
    )

    col_coord, col_al = st.columns(2)
    with col_coord:
        st.markdown("**Alerta para a Coordenação (Técnico)**")
        st.text_area("coord", value=pacote["msg_coordenacao"], height=210, label_visibility="collapsed")
    with col_al:
        st.markdown("**Alerta para o Estudante (Empático)**")
        st.text_area("aluno", value=pacote["msg_aluno"], height=210, label_visibility="collapsed")

    if st.button("Disparar alertas agora (Coordenação + Estudante)", type="primary"):
        agente.disparar_e_registrar(aluno_sel["id"], aluno_sel["resultado_ml"], pacote)
        st.success(f"Alertas disparados e auditados para {aluno_sel['nome']} e para a Coordenação.")

    st.divider()
    st.markdown("**Histórico de Disparos Auditados**")
    with SessionLocal() as db:
        logs = db.query(LogAlerta).order_by(LogAlerta.criado_em.desc()).limit(10).all()
        if not logs:
            st.caption("Nenhum alerta disparado ainda.")
        else:
            st.dataframe(
                [
                    {
                        "Data": l.criado_em.strftime("%d/%m/%Y %H:%M"),
                        "Estudante": l.aluno.nome,
                        "Diagnóstico": l.diagnostico_ml,
                        "Prioridade": l.prioridade,
                        "Status": l.status_envio,
                    }
                    for l in logs
                ],
                use_container_width=True,
                hide_index=True,
            )

with aba_sim:
    st.subheader("Cadastrar Novo Estudante e Testar Predição ao Vivo")
    with st.form("form_novo_aluno", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Nome completo")
        matricula = c2.text_input("Matrícula")
        curso = c3.text_input("Curso", value="Análise e Desenv. de Sistemas")

        c4, c5, c6 = st.columns(3)
        semestre = c4.number_input("Semestre", 1, 10, 2)
        email = c5.text_input("E-mail do estudante")
        satisfacao = c6.slider("Satisfação com o curso (1 a 5)", 1, 5, 3)

        c7, c8, c9, c10 = st.columns(4)
        nota = c7.number_input("Média de notas", 0.0, 10.0, 6.5, 0.1)
        freq = c8.number_input("Frequência (%)", 0.0, 100.0, 80.0, 1.0)
        ava = c9.number_input("Acessos AVA / semana", 0, 30, 5)
        atraso = c10.number_input("Dias de atraso mensalidade", 0, 120, 0)
        reprov = st.number_input("Reprovações acumuladas", 0, 15, 0)

        if st.form_submit_button("Salvar e analisar com IA", type="primary"):
            if not (nome.strip() and matricula.strip()):
                st.error("Preencha nome e matrícula.")
            else:
                with SessionLocal() as db:
                    db.add(Aluno(
                        matricula=matricula.strip(),
                        nome=nome.strip(),
                        curso=curso.strip(),
                        semestre=int(semestre),
                        email_aluno=email.strip() or "aluno@faculdade.edu",
                        media_notas=float(nota),
                        frequencia_pct=float(freq),
                        acessos_ava_semana=int(ava),
                        reprovacoes=int(reprov),
                        dias_atraso_mensalidade=int(atraso),
                        satisfacao_curso=int(satisfacao),
                    ))
                    db.commit()
                st.success("Estudante cadastrado e avaliado pelo modelo de ML.")
                st.rerun()
