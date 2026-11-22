import io
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy.exc import IntegrityError
from database import SessionLocal, Aluno, Desempenho, inicializar_banco
from alertas import avaliar_risco
from modelo_ml import treinar_modelo, prever_risco_ml

st.set_page_config(
    page_title="EduAlerta | Inteligência Acadêmica",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo visual institucional
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #2563eb;
        padding: 14px 16px;
        border-radius: 10px;
    }
    .banner-header {
        background: linear-gradient(90deg, #0f172a 0%, #1e3a8a 100%);
        color: white;
        padding: 1.2rem 1.6rem;
        border-radius: 12px;
        margin-bottom: 1.2rem;
    }
    .banner-header h2 { margin: 0; font-size: 1.6rem; color: white; }
    .banner-header p { margin: 4px 0 0 0; opacity: 0.88; font-size: 0.95rem; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def iniciar_estrutura():
    inicializar_banco()

@st.cache_resource
def carregar_ia():
    return treinar_modelo()

iniciar_estrutura()
modelo_ia, acuracia_ia, df_importancias = carregar_ia()

def limpar_numero(valor, padrao=0.0):
    if pd.isna(valor):
        return padrao
    return float(str(valor).replace(",", ".").replace("%", "").strip())

def carregar_dataframe():
    with SessionLocal() as db:
        registros = db.query(Desempenho).join(Aluno).all()
        linhas = []
        for r in registros:
            ativ = r.atividades if r.atividades is not None else 100.0
            alerta = avaliar_risco(r.nota, r.frequencia)
            prev = prever_risco_ml(modelo_ia, r.nota, r.frequencia, ativ)
            linhas.append({
                "Matrícula": r.aluno.matricula,
                "Aluno": r.aluno.nome,
                "Turma/Curso": r.aluno.turma,
                "E-mail": r.aluno.email_responsavel or "-",
                "Disciplina": r.disciplina,
                "Período": r.periodo,
                "Nota": round(r.nota, 1),
                "Frequência (%)": round(r.frequencia, 1),
                "Atividades (%)": round(ativ, 1),
                "Status (Regra)": alerta["nivel"],
                "Risco IA (%)": prev["probabilidade"],
                "Previsão IA": prev["faixa"],
                "Motivo": alerta["motivo"],
                "Ação Recomendada": prev["recomendacao"]
            })
        return pd.DataFrame(linhas)

def popular_dados_demo():
    amostra = [
        ("Ana Beatriz Silva", "2026101", "ADS - 2º Período", "ana@instituicao.edu", "Algoritmos", "1º Semestre", 8.8, 96, 95),
        ("Ana Beatriz Silva", "2026101", "ADS - 2º Período", "ana@instituicao.edu", "Banco de Dados", "1º Semestre", 8.2, 92, 90),
        ("Bruno Henrique Costa", "2026102", "ADS - 2º Período", "bruno@instituicao.edu", "Algoritmos", "1º Semestre", 6.4, 80, 35),
        ("Bruno Henrique Costa", "2026102", "ADS - 2º Período", "bruno@instituicao.edu", "Banco de Dados", "1º Semestre", 5.8, 76, 40),
        ("Carla Mendes Rocha", "2026103", "ADS - 2º Período", "carla@instituicao.edu", "Algoritmos", "1º Semestre", 3.9, 64, 20),
        ("Carla Mendes Rocha", "2026103", "ADS - 2º Período", "carla@instituicao.edu", "Cálculo I", "1º Semestre", 4.2, 68, 25),
        ("Diego Lima Souza", "2026104", "3º Ano A - Médio", "resp.diego@email.com", "Matemática", "1º Bimestre", 7.5, 88, 85),
        ("Diego Lima Souza", "2026104", "3º Ano A - Médio", "resp.diego@email.com", "Matemática", "2º Bimestre", 5.6, 78, 45),
        ("Fernanda Alves", "2026105", "3º Ano A - Médio", "resp.fernanda@email.com", "Física", "1º Bimestre", 4.8, 72, 30),
        ("Gabriel Oliveira", "2026106", "3º Ano A - Médio", "resp.gabriel@email.com", "Física", "1º Bimestre", 9.1, 98, 100),
    ]
    with SessionLocal() as db:
        for nome, mat, turma, email, disc, per, nota, freq, ativ in amostra:
            aluno = db.query(Aluno).filter(Aluno.matricula == mat).first()
            if not aluno:
                aluno = Aluno(nome=nome, matricula=mat, turma=turma, email_responsavel=email)
                db.add(aluno)
                db.flush()
            db.add(Desempenho(
                aluno_id=aluno.id, disciplina=disc, periodo=per,
                nota=nota, frequencia=freq, atividades=ativ
            ))
        db.commit()

# Menu Lateral
with st.sidebar:
    st.title("🎓 EduAlerta")
    st.caption("Learning Analytics & Prevenção")
    pagina = st.radio(
        "Navegação",
        [
            "Visão Executiva",
            "Ficha Individual do Aluno",
            "Simulador Preditivo (IA)",
            "Importar do Portal (CSV/Excel)",
            "Cadastros Manuais",
            "Integrar em Portais"
        ]
    )
    st.divider()
    st.caption(f"Modelo: Random Forest | Acurácia: **{acuracia_ia}%**")
    if st.button("⚡ Carregar Dados Demo", use_container_width=True):
        popular_dados_demo()
        st.success("Base demonstrativa carregada!")
        st.rerun()

# Cabeçalho
st.markdown("""
<div class="banner-header">
    <h2>EduAlerta — Plataforma de Controle e Alerta Acadêmico</h2>
    <p>Monitoramento contínuo de notas, frequência e engajamento com Machine Learning preventivo.</p>
</div>
""", unsafe_allow_html=True)

df = carregar_dataframe()

# 1. VISÃO EXECUTIVA
if pagina == "Visão Executiva":
    if df.empty:
        st.info("Nenhum registro acadêmico no banco ainda. Use o botão **'Carregar Dados Demo'** no menu lateral ou importe uma planilha em **'Importar do Portal'**.")
    else:
        col_f1, col_f2, col_f3 = st.columns(3)
        turmas_sel = col_f1.multiselect("Turma / Curso", sorted(df["Turma/Curso"].unique()), default=sorted(df["Turma/Curso"].unique()))
        disc_sel = col_f2.multiselect("Disciplina", sorted(df["Disciplina"].unique()), default=sorted(df["Disciplina"].unique()))
        risco_sel = col_f3.multiselect("Classificação IA", ["ALTO RISCO", "RISCO MODERADO", "BAIXO RISCO"], default=["ALTO RISCO", "RISCO MODERADO", "BAIXO RISCO"])

        df_f = df[
            df["Turma/Curso"].isin(turmas_sel) &
            df["Disciplina"].isin(disc_sel) &
            df["Previsão IA"].isin(risco_sel)
        ]

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Alunos Monitorados", df_f["Matrícula"].nunique())
        k2.metric("Média Geral", f"{df_f['Nota'].mean():.1f}" if not df_f.empty else "-")
        k3.metric("Frequência Média", f"{df_f['Frequência (%)'].mean():.0f}%" if not df_f.empty else "-")
        k4.metric("Alto Risco (IA)", int((df_f["Previsão IA"] == "ALTO RISCO").sum()))
        k5.metric("Críticos (Regra)", int((df_f["Status (Regra)"] == "CRÍTICO").sum()))

        st.divider()
        g1, g2 = st.columns([3, 2])

        with g1:
            st.subheader("Mapa de Risco: Frequência × Nota")
            fig_disp = px.scatter(
                df_f, x="Frequência (%)", y="Nota", color="Previsão IA",
                size="Risco IA (%)", hover_data=["Aluno", "Turma/Curso", "Disciplina", "Atividades (%)"],
                color_discrete_map={"ALTO RISCO": "#dc2626", "RISCO MODERADO": "#f59e0b", "BAIXO RISCO": "#16a34a"}
            )
            fig_disp.add_hline(y=7.0, line_dash="dash", line_color="#64748b", annotation_text="Média 7,0")
            fig_disp.add_vline(x=75.0, line_dash="dash", line_color="#dc2626", annotation_text="Mínimo LDB 75%")
            fig_disp.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig_disp, use_container_width=True)

        with g2:
            st.subheader("Disciplinas Gargalo (Risco Médio IA)")
            gargalo = df_f.groupby("Disciplina", as_index=False)["Risco IA (%)"].mean().sort_values("Risco IA (%)", ascending=True)
            fig_bar = px.bar(
                gargalo, x="Risco IA (%)", y="Disciplina", orientation="h",
                color="Risco IA (%)", color_continuous_scale=["#16a34a", "#f59e0b", "#dc2626"]
            )
            fig_bar.update_layout(height=380, showlegend=False, coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("Painel Detalhado de Alertas e Planos de Ação")
        st.dataframe(
            df_f.sort_values("Risco IA (%)", ascending=False),
            use_container_width=True,
            hide_index=True
        )

        csv_export = df_f.to_csv(index=False, sep=";").encode("utf-8-sig")
        st.download_button(
            "📥 Exportar Relatório para Conselho de Classe (CSV)",
            data=csv_export,
            file_name="relatorio_edualerta.csv",
            mime="text/csv"
        )

# 2. FICHA INDIVIDUAL DO ALUNO
elif pagina == "Ficha Individual do Aluno":
    if df.empty:
        st.info("Cadastre ou importe dados primeiro para consultar a ficha individual.")
    else:
        aluno_sel = st.selectbox("Selecione o estudante", sorted(df["Aluno"].unique()))
        df_a = df[df["Aluno"] == aluno_sel]
        turma_aluno = df_a["Turma/Curso"].iloc[0]
        media_turma = df[df["Turma/Curso"] == turma_aluno]["Nota"].mean()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Turma / Curso", turma_aluno)
        c2.metric("Média do Aluno", f"{df_a['Nota'].mean():.1f}", delta=f"{df_a['Nota'].mean() - media_turma:+.1f} vs turma")
        c3.metric("Frequência Média", f"{df_a['Frequência (%)'].mean():.0f}%")
        c4.metric("Maior Risco IA", f"{df_a['Risco IA (%)'].max():.1f}%")

        fig_evo = px.bar(
            df_a, x="Disciplina", y="Nota", color="Período", barmode="group",
            title=f"Desempenho por Disciplina e Período — {aluno_sel}"
        )
        fig_evo.add_hline(y=7.0, line_dash="dash", line_color="#16a34a")
        st.plotly_chart(fig_evo, use_container_width=True)

        st.subheader("Diagnóstico e Recomendações Pedagógicas")
        st.dataframe(
            df_a[["Disciplina", "Período", "Nota", "Frequência (%)", "Atividades (%)", "Previsão IA", "Ação Recomendada"]],
            use_container_width=True,
            hide_index=True
        )

# 3. SIMULADOR PREDITIVO (IA)
elif pagina == "Simulador Preditivo (IA)":
    col_sim, col_exp = st.columns([3, 2])
    with col_sim:
        st.subheader("Simulação em Tempo Real (Random Forest)")
        s_nota = st.slider("Nota atual (0 a 10)", 0.0, 10.0, 6.2, 0.1)
        s_freq = st.slider("Frequência (%)", 40, 100, 78, 1)
        s_ativ = st.slider("Atividades entregues no portal (%)", 0, 100, 35, 5)

        res = prever_risco_ml(modelo_ia, s_nota, s_freq, s_ativ)
        m1, m2 = st.columns(2)
        m1.metric("Probabilidade de Risco (IA)", f"{res['probabilidade']}%")
        m2.metric("Classificação", res["faixa"])

        if res["faixa"] == "ALTO RISCO":
            st.error(f"**Plano de ação sugerido:** {res['recomendacao']}")
        elif res["faixa"] == "RISCO MODERADO":
            st.warning(f"**Plano de ação sugerido:** {res['recomendacao']}")
        else:
            st.success(f"**Situação estável:** {res['recomendacao']}")

    with col_exp:
        st.subheader("Peso das Variáveis na IA")
        fig_imp = px.bar(df_importancias, x="Peso (%)", y="Fator", orientation="h", text="Peso (%)")
        fig_imp.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_imp, use_container_width=True)
        st.caption(f"Acurácia de validação do modelo: **{acuracia_ia}%** (divisão 80/20).")

# 4. IMPORTAR DO PORTAL (CSV / EXCEL)
elif pagina == "Importar do Portal (CSV/Excel)":
    st.subheader("Importação em Lote (TOTVS RM, SIGAA, Moodle, Classroom)")
    st.write("Exporte o boletim do portal da escola ou faculdade no formato modelo abaixo e suba aqui para análise imediata com IA.")

    modelo_planilha = pd.DataFrame([
        {
            "nome": "Lucas Pereira", "matricula": "2026901", "turma": "ADS - 1º Período",
            "email_responsavel": "lucas@faculdade.edu", "disciplina": "Programação Web",
            "periodo": "1º Semestre", "nota": 6.0, "frequencia": 74, "atividades": 40
        },
        {
            "nome": "Mariana Santos", "matricula": "2026902", "turma": "ADS - 1º Período",
            "email_responsavel": "mariana@faculdade.edu", "disciplina": "Programação Web",
            "periodo": "1º Semestre", "nota": 9.0, "frequencia": 95, "atividades": 100
        }
    ])

    buffer_xlsx = io.BytesIO()
    modelo_planilha.to_excel(buffer_xlsx, index=False)
    st.download_button(
        "📄 Baixar Planilha Modelo (.xlsx)",
        data=buffer_xlsx.getvalue(),
        file_name="modelo_importacao_edualerta.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    arquivo = st.file_uploader("Envie a planilha do portal (.csv ou .xlsx)", type=["csv", "xlsx"])
    if arquivo:
        try:
            if arquivo.name.endswith(".csv"):
                df_up = pd.read_csv(arquivo, sep=None, engine="python")
            else:
                df_up = pd.read_excel(arquivo)

            df_up.columns = [c.strip().lower() for c in df_up.columns]
            st.write("Pré-visualização dos dados encontrados:")
            st.dataframe(df_up.head(10), use_container_width=True)

            colunas_obrigatorias = {"nome", "matricula", "turma", "disciplina", "periodo", "nota", "frequencia"}
            faltando = colunas_obrigatorias - set(df_up.columns)

            if faltando:
                st.error(f"Colunas obrigatórias ausentes na planilha: {', '.join(sorted(faltando))}")
            elif st.button("🚀 Confirmar Importação para o Banco na Nuvem", type="primary"):
                inseridos = 0
                with SessionLocal() as db:
                    for _, row in df_up.iterrows():
                        mat = str(row["matricula"]).strip()
                        aluno = db.query(Aluno).filter(Aluno.matricula == mat).first()
                        if not aluno:
                            aluno = Aluno(
                                nome=str(row["nome"]).strip(),
                                matricula=mat,
                                turma=str(row["turma"]).strip(),
                                email_responsavel=str(row.get("email_responsavel", "")).strip()
                            )
                            db.add(aluno)
                            db.flush()
                        db.add(Desempenho(
                            aluno_id=aluno.id,
                            disciplina=str(row["disciplina"]).strip(),
                            periodo=str(row["periodo"]).strip(),
                            nota=limpar_numero(row["nota"]),
                            frequencia=limpar_numero(row["frequencia"]),
                            atividades=limpar_numero(row.get("atividades", 100.0), 100.0)
                        ))
                        inseridos += 1
                    db.commit()
                st.success(f"{inseridos} registros importados e analisados com sucesso!")
        except Exception as erro:
            st.error(f"Erro ao ler a planilha: {erro}")

# 5. CADASTROS MANUAIS
elif pagina == "Cadastros Manuais":
    aba1, aba2 = st.tabs(["Cadastrar Aluno", "Lançar Desempenho"])
    with aba1:
        with st.form("form_aluno", clear_on_submit=True):
            nome = st.text_input("Nome completo")
            matricula = st.text_input("Matrícula")
            turma = st.text_input("Turma / Curso (ex.: ADS - 2º Período ou 3º Ano A)")
            email = st.text_input("E-mail do aluno ou responsável")
            if st.form_submit_button("Salvar Aluno"):
                if nome and matricula and turma:
                    try:
                        with SessionLocal() as db:
                            db.add(Aluno(nome=nome, matricula=matricula, turma=turma, email_responsavel=email))
                            db.commit()
                        st.success("Aluno cadastrado com sucesso.")
                    except IntegrityError:
                        st.error("Já existe um aluno cadastrado com essa matrícula.")
                else:
                    st.warning("Preencha nome, matrícula e turma/curso.")

    with aba2:
        with SessionLocal() as db:
            alunos = db.query(Aluno).order_by(Aluno.nome).all()
        if not alunos:
            st.info("Cadastre ao menos um aluno antes de lançar desempenho.")
        else:
            mapa = {f"{a.nome} ({a.matricula})": a.id for a in alunos}
            with st.form("form_desempenho", clear_on_submit=True):
                aluno_sel = st.selectbox("Aluno", list(mapa.keys()))
                disciplina = st.text_input("Disciplina")
                periodo = st.selectbox("Período", ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre", "1º Semestre", "2º Semestre"])
                nota = st.number_input("Nota (0 a 10)", 0.0, 10.0, 7.0, 0.5)
                frequencia = st.number_input("Frequência (%)", 0.0, 100.0, 90.0, 1.0)
                atividades = st.number_input("Atividades entregues (%)", 0.0, 100.0, 80.0, 5.0)
                if st.form_submit_button("Registrar Desempenho"):
                    if disciplina:
                        with SessionLocal() as db:
                            db.add(Desempenho(
                                aluno_id=mapa[aluno_sel], disciplina=disciplina, periodo=periodo,
                                nota=nota, frequencia=frequencia, atividades=atividades
                            ))
                            db.commit()
                        st.success("Lançamento registrado e classificado pela IA.")
                    else:
                        st.warning("Informe o nome da disciplina.")

# 6. INTEGRAR EM PORTAIS
elif pagina == "Integrar em Portais":
    st.subheader("Como Embutir o EduAlerta no Portal da Escola ou Faculdade")
    st.write("Cole o código HTML abaixo dentro de uma página do **Moodle**, **Google Sites**, **WordPress** ou **Intranet Acadêmica** para exibir o painel diretamente no portal da instituição:")
    st.code(
        '<iframe src="https://edualerta.streamlit.app/?embed=true" width="100%" height="850" style="border:none; border-radius:10px;"></iframe>',
        language="html"
    )
    st.subheader("Arquitetura de Integração Automática (API / ETL)")
    st.markdown("""
    * **Nível 1 (Ativo agora):** Importação em lote via planilhas `.xlsx`/`.csv` exportadas do TOTVS RM, SIGAA, Lyceum ou Classroom.
    * **Nível 2 (Ativo agora):** Incorporação visual em portais internos via `<iframe>` com protocolo HTTPS.
    * **Nível 3 (Expansão corporativa):** Microsserviço **FastAPI** conectado ao mesmo PostgreSQL recebendo webhooks automáticos de lançamento de notas via *API Key*.
    """)
