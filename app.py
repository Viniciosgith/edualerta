import streamlit as st
import pandas as pd
from database import SessionLocal, Aluno, Desempenho, inicializar_banco
from alertas import avaliar_risco

st.set_page_config(page_title="EduAlerta - Controle Escolar", layout="wide")
inicializar_banco()
db = SessionLocal()

st.title("EduAlerta — Controle e Alerta de Desempenho Escolar")

aba_dashboard, aba_cadastro, aba_lancamento = st.tabs([
    "Painel de Alertas", "Cadastrar Aluno", "Lançar Desempenho"
])

with aba_cadastro:
    st.subheader("Novo Aluno")
    with st.form("form_aluno", clear_on_submit=True):
        nome = st.text_input("Nome completo")
        matricula = st.text_input("Matrícula")
        turma = st.text_input("Turma (ex.: 3º Ano A)")
        email = st.text_input("E-mail do responsável")
        if st.form_submit_button("Salvar Aluno"):
            if nome and matricula and turma:
                db.add(Aluno(nome=nome, matricula=matricula, turma=turma, email_responsavel=email))
                db.commit()
                st.success("Aluno cadastrado com sucesso.")
            else:
                st.warning("Preencha nome, matrícula e turma.")

with aba_lancamento:
    st.subheader("Registrar Nota e Frequência")
    alunos = db.query(Aluno).all()
    if not alunos:
        st.info("Cadastre ao menos um aluno primeiro.")
    else:
        mapa_alunos = {f"{a.nome} ({a.matricula})": a.id for a in alunos}
        with st.form("form_desempenho", clear_on_submit=True):
            aluno_sel = st.selectbox("Aluno", list(mapa_alunos.keys()))
            disciplina = st.text_input("Disciplina")
            periodo = st.selectbox("Período", ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre"])
            nota = st.number_input("Nota (0 a 10)", min_value=0.0, max_value=10.0, step=0.5)
            frequencia = st.number_input("Frequência (%)", min_value=0.0, max_value=100.0, value=90.0, step=1.0)
            if st.form_submit_button("Registrar"):
                db.add(Desempenho(
                    aluno_id=mapa_alunos[aluno_sel],
                    disciplina=disciplina,
                    periodo=periodo,
                    nota=nota,
                    frequencia=frequencia
                ))
                db.commit()
                st.success("Desempenho registrado.")

with aba_dashboard:
    registros = db.query(Desempenho).join(Aluno).all()
    if not registros:
        st.info("Nenhum lançamento encontrado.")
    else:
        dados = []
        for r in registros:
            alerta = avaliar_risco(r.nota, r.frequencia)
            dados.append({
                "Aluno": r.aluno.nome,
                "Turma": r.aluno.turma,
                "Disciplina": r.disciplina,
                "Período": r.periodo,
                "Nota": r.nota,
                "Frequência (%)": r.frequencia,
                "Status": alerta["nivel"],
                "Motivo do Alerta": alerta["motivo"]
            })
        df = pd.DataFrame(dados)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Registros", len(df))
        c2.metric("Alertas Críticos", int((df["Status"] == "CRÍTICO").sum()))
        c3.metric("Em Atenção", int((df["Status"] == "ATENÇÃO").sum()))

        filtro = st.multiselect("Filtrar por Status", ["CRÍTICO", "ATENÇÃO", "NORMAL"], default=["CRÍTICO", "ATENÇÃO"])
        st.dataframe(df[df["Status"].isin(filtro)], use_container_width=True)