import io
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy.exc import IntegrityError
from database import SessionLocal, Aluno, Desempenho, Intervencao, inicializar_banco
from alertas import avaliar_risco, gerar_mensagem_alerta, enviar_email_alerta
from modelo_ml import treinar_modelo, prever_risco_ml

st.set_page_config(
    page_title="EduAlerta | Plataforma de Inteligência Acadêmica",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS institucional refinado (compatível com o tema claro do config.toml)
st.markdown("""
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-top: 3px solid #1d4ed8;
        padding: 16px 18px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
    }
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 65%, #1d4ed8 100%);
        color: #ffffff;
        padding: 1.35rem 1.75rem;
        border-radius: 12px;
        margin-bottom: 1.4rem;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
    }
    .hero-banner h2 { margin: 0; font-size: 1.55rem; font-weight: 700; color: #ffffff; }
    .hero-banner p { margin: 6px 0 0 0; font-size: 0.94rem; color: #cbd5e1; }
    .login-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 2rem;
        box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def iniciar_estrutura():
    inicializar_banco()

@st.cache_resource
def carregar_ia():
    return treinar_modelo()

iniciar_estrutura()
modelo_ia, metricas_ia, matriz_confusao, df_importancias = carregar_ia()

# Controle de acesso institucional (configurável via Secrets)
ADMIN_USER = os.getenv("ADMIN_USER", "coordenacao")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "edualerta2026")
MODO_EMBED = st.query_params.get("embed") == "true"

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = MODO_EMBED

if not st.session_state["autenticado"]:
    _, col_centro, _ = st.columns([1, 1.3, 1])
    with col_centro:
        st.markdown("""
        <div class="hero-banner" style="text-align:center; margin-top: 2rem;">
            <h2>🎓 EduAlerta</h2>
            <p>Plataforma de Learning Analytics e Alerta Preventivo</p>
        </div>
        """, unsafe_allow_html=True)
        with st.form("form_login"):
            st.subheader("Acesso Institucional")
            usuario = st.text_input("Usuário", placeholder="coordenacao")
            senha = st.text_input("Senha", type="password", placeholder="••••••••")
            entrar = st.form_submit_button("Entrar na Plataforma", type="primary", use_container_width=True)
            if entrar:
                if usuario.strip() == ADMIN_USER and senha == ADMIN_PASSWORD:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_nome"] = usuario.strip()
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
        st.info("**Acesso de demonstração:** usuário `coordenacao` | senha `edualerta2026`")
    st.stop()

def limpar_numero(valor, padrao=0.0):
    if pd.isna(valor):
        return padrao
    texto = str(valor).replace(",", ".").replace("%", "").strip()
    try:
        return float(texto)
    except ValueError:
        return padrao

def carregar_dataframe():
    with SessionLocal() as db:
        registros = db.query(Desempenho).join(Aluno).all()
        linhas = []
        for r in registros:
            ativ = r.atividades if r.atividades is not None else 100.0
            alerta = avaliar_risco(r.nota, r.frequencia)
            prev = prever_risco_ml(modelo_ia, r.nota, r.frequencia, ativ)
            linhas.append({
                "ID": r.id,
                "Aluno_ID": r.aluno.id,
                "Matrícula": r.aluno.matricula,
                "Aluno": r.aluno.nome,
                "Turma/Curso": r.aluno.turma,
                "E-mail": r.aluno.email_responsavel or "",
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
        ("Diego Lima Souza", "2026104", "3º Ano A - Médio", "resp.diego@email.com", "Matemática", "1º Bimestre", 7.6, 90, 85),
        ("Diego Lima Souza", "2026104", "3º Ano A - Médio", "resp.diego@email.com", "Matemática", "2º Bimestre", 5.5, 78, 42),
        ("Fernanda Alves", "2026105", "3º Ano A - Médio", "resp.fernanda@email.com", "Física", "1º Bimestre", 4.6, 71, 30),
        ("Gabriel Oliveira", "2026106", "3º Ano A - Médio", "resp.gabriel@email.com", "Física", "1º Bimestre", 9.2, 98, 100),
    ]
    inseridos = 0
    with SessionLocal() as db:
        for nome, mat, turma, email, disc, per, nota, freq, ativ in amostra:
            aluno = db.query(Aluno).filter(Aluno.matricula == mat).first()
            if not aluno:
                aluno = Aluno(nome=nome, matricula=mat, turma=turma, email_responsavel=email)
                db.add(aluno)
                db.flush()
            existe = db.query(Desempenho).filter(
                Desempenho.aluno_id == aluno.id,
                Desempenho.disciplina == disc,
                Desempenho.periodo == per
            ).first()
            if not existe:
                db.add(Desempenho(
                    aluno_id=aluno.id, disciplina=disc, periodo=per,
                    nota=nota, frequencia=freq, atividades=ativ
                ))
                inseridos += 1
        db.commit()
    return inseridos

# Navegação Lateral
with st.sidebar:
    st.markdown("### 🎓 EduAlerta Pro")
    st.caption("Inteligência Acadêmica & Permanência")
    st.divider()
    pagina = st.radio(
        "Módulos",
        [
            "Visão Executiva",
            "Ficha & Intervenções",
            "Central de Alertas",
            "Simulador & Auditoria IA",
            "Importar do Portal",
            "Gestão de Cadastros",
            "Integrar em Portais"
        ]
    )
    st.divider()
    st.caption(f"Random Forest • F1-Score: **{metricas_ia['f1']}%**")
    if st.button("⚡ Popular Base Demo", use_container_width=True):
        qtd = popular_dados_demo()
        if qtd > 0:
            st.success(f"{qtd} registros demonstrativos adicionados.")
            st.rerun()
        else:
            st.info("Os dados demonstrativos já estão carregados.")
    if not MODO_EMBED and st.button("Sair", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()

# Banner superior (ocultado no modo iframe compacto)
if not MODO_EMBED:
    st.markdown("""
    <div class="hero-banner">
        <h2>EduAlerta — Controle Preventivo de Desempenho Escolar</h2>
        <p>Monitoramento contínuo de notas, frequência, engajamento e intervenções pedagógicas com Machine Learning.</p>
    </div>
    """, unsafe_allow_html=True)

df = carregar_dataframe()

# ==========================================
# 1. VISÃO EXECUTIVA
# ==========================================
if pagina == "Visão Executiva":
    if df.empty:
        st.info("Nenhum dado acadêmico cadastrado ainda. Clique em **'⚡ Popular Base Demo'** na barra lateral ou envie uma planilha em **'Importar do Portal'**.")
    else:
        f1, f2, f3 = st.columns(3)
        turmas = sorted(df["Turma/Curso"].unique())
        discs = sorted(df["Disciplina"].unique())
        turmas_sel = f1.multiselect("Turma / Curso", turmas, default=turmas)
        disc_sel = f2.multiselect("Disciplina", discs, default=discs)
        risco_sel = f3.multiselect(
            "Classificação da IA",
            ["ALTO RISCO", "RISCO MODERADO", "BAIXO RISCO"],
            default=["ALTO RISCO", "RISCO MODERADO", "BAIXO RISCO"]
        )

        df_f = df[
            df["Turma/Curso"].isin(turmas_sel) &
            df["Disciplina"].isin(disc_sel) &
            df["Previsão IA"].isin(risco_sel)
        ]

        with SessionLocal() as db:
            intervencoes_abertas = db.query(Intervencao).filter(Intervencao.status != "Concluído").count()

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Estudantes", df_f["Matrícula"].nunique())
        k2.metric("Média Geral", f"{df_f['Nota'].mean():.1f}" if not df_f.empty else "-")
        k3.metric("Frequência Média", f"{df_f['Frequência (%)'].mean():.0f}%" if not df_f.empty else "-")
        k4.metric("Alto Risco (IA)", int((df_f["Previsão IA"] == "ALTO RISCO").sum()))
        k5.metric("Ações em Aberto", intervencoes_abertas)

        st.markdown("")
        g1, g2 = st.columns([3, 2])
        with g1:
            st.subheader("Mapa de Risco: Frequência × Nota")
            fig_disp = px.scatter(
                df_f, x="Frequência (%)", y="Nota", color="Previsão IA",
                size="Risco IA (%)", template="plotly_white",
                hover_data=["Aluno", "Turma/Curso", "Disciplina", "Atividades (%)"],
                color_discrete_map={"ALTO RISCO": "#dc2626", "RISCO MODERADO": "#d97706", "BAIXO RISCO": "#16a34a"}
            )
            fig_disp.add_hline(y=7.0, line_dash="dash", line_color="#64748b", annotation_text="Média 7,0")
            fig_disp.add_vline(x=75.0, line_dash="dash", line_color="#dc2626", annotation_text="LDB 75%")
            fig_disp.update_layout(height=370, margin=dict(l=10, r=10, t=15, b=10))
            st.plotly_chart(fig_disp, use_container_width=True)

        with g2:
            st.subheader("Disciplinas Gargalo (Risco Médio)")
            gargalo = df_f.groupby("Disciplina", as_index=False)["Risco IA (%)"].mean().sort_values("Risco IA (%)", ascending=True)
            fig_bar = px.bar(
                gargalo, x="Risco IA (%)", y="Disciplina", orientation="h",
                template="plotly_white", color="Risco IA (%)",
                color_continuous_scale=["#16a34a", "#f59e0b", "#dc2626"]
            )
            fig_bar.update_layout(height=370, showlegend=False, coloraxis_showscale=False, margin=dict(l=10, r=10, t=15, b=10))
            st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("Prioridade de Intervenção Pedagógica")
        colunas_exibir = [
            "Aluno", "Turma/Curso", "Disciplina", "Período",
            "Nota", "Frequência (%)", "Atividades (%)", "Risco IA (%)", "Previsão IA", "Ação Recomendada"
        ]
        st.dataframe(
            df_f[colunas_exibir].sort_values("Risco IA (%)", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Nota": st.column_config.NumberColumn("Nota", format="%.1f"),
                "Frequência (%)": st.column_config.ProgressColumn("Frequência", min_value=0, max_value=100, format="%.0f%%"),
                "Atividades (%)": st.column_config.ProgressColumn("Atividades", min_value=0, max_value=100, format="%.0f%%"),
                "Risco IA (%)": st.column_config.ProgressColumn("Risco IA", min_value=0, max_value=100, format="%.1f%%"),
            }
        )

        csv_export = df_f[colunas_exibir].to_csv(index=False, sep=";").encode("utf-8-sig")
        st.download_button(
            "📥 Exportar Relatório para Conselho de Classe (CSV)",
            data=csv_export,
            file_name="relatorio_conselho_edualerta.csv",
            mime="text/csv"
        )

# ==========================================
# 2. FICHA INDIVIDUAL & INTERVENÇÕES
# ==========================================
elif pagina == "Ficha & Intervenções":
    if df.empty:
        st.info("Cadastre ou importe registros primeiro.")
    else:
        aluno_sel = st.selectbox("Selecione o estudante", sorted(df["Aluno"].unique()))
        df_a = df[df["Aluno"] == aluno_sel]
        aluno_id = int(df_a["Aluno_ID"].iloc[0])
        turma_aluno = df_a["Turma/Curso"].iloc[0]
        media_turma = df[df["Turma/Curso"] == turma_aluno]["Nota"].mean()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Turma / Curso", turma_aluno)
        c2.metric("Média do Aluno", f"{df_a['Nota'].mean():.1f}", delta=f"{df_a['Nota'].mean() - media_turma:+.1f} vs turma")
        c3.metric("Frequência Média", f"{df_a['Frequência (%)'].mean():.0f}%")
        c4.metric("Maior Risco IA", f"{df_a['Risco IA (%)'].max():.1f}%")

        fig_evo = px.bar(
            df_a, x="Disciplina", y="Nota", color="Período", barmode="group",
            template="plotly_white", title=f"Desempenho por Disciplina — {aluno_sel}"
        )
        fig_evo.add_hline(y=7.0, line_dash="dash", line_color="#16a34a")
        st.plotly_chart(fig_evo, use_container_width=True)

        col_hist, col_nova = st.columns([3, 2])
        with col_hist:
            st.subheader("Histórico de Intervenções Pedagógicas")
            with SessionLocal() as db:
                acoes = db.query(Intervencao).filter(Intervencao.aluno_id == aluno_id).order_by(Intervencao.criado_em.desc()).all()
            if not acoes:
                st.info("Nenhuma intervenção registrada para este estudante.")
            else:
                df_int = pd.DataFrame([{
                    "Data": a.criado_em.strftime("%d/%m/%Y %H:%M"),
                    "Tipo": a.tipo,
                    "Responsável": a.responsavel_acao,
                    "Status": a.status,
                    "Observação": a.observacao or "-"
                } for a in acoes])
                st.dataframe(df_int, use_container_width=True, hide_index=True)

        with col_nova:
            st.subheader("Registrar Nova Ação")
            with st.form("form_intervencao", clear_on_submit=True):
                tipo = st.selectbox("Tipo de intervenção", [
                    "Contato com responsável / estudante",
                    "Encaminhamento para monitoria",
                    "Reunião com coordenação pedagógica",
                    "Plano de recuperação paralela",
                    "Apoio psicopedagógico (NAE)"
                ])
                resp_acao = st.text_input("Responsável pela ação", value="Coordenação Pedagógica")
                status = st.selectbox("Status", ["Pendente", "Em andamento", "Concluído"])
                obs = st.text_area("Observações / Combinados")
                if st.form_submit_button("Salvar Intervenção", type="primary", use_container_width=True):
                    with SessionLocal() as db:
                        db.add(Intervencao(
                            aluno_id=aluno_id, tipo=tipo, responsavel_acao=resp_acao,
                            status=status, observacao=obs
                        ))
                        db.commit()
                    st.success("Intervenção salva no prontuário do estudante.")
                    st.rerun()

# ==========================================
# 3. CENTRAL DE ALERTAS (E-MAIL / WHATSAPP)
# ==========================================
elif pagina == "Central de Alertas":
    st.subheader("Disparo de Notificações Preventivas")
    df_risco = df[df["Previsão IA"].isin(["ALTO RISCO", "RISCO MODERADO"])] if not df.empty else pd.DataFrame()

    if df_risco.empty:
        st.success("Nenhum estudante em faixa de risco moderado ou alto no momento.")
    else:
        opcoes = {
            f"{row['Aluno']} — {row['Disciplina']} (Risco IA: {row['Risco IA (%)']}%)": idx
            for idx, row in df_risco.sort_values("Risco IA (%)", ascending=False).iterrows()
        }
        selecao = st.selectbox("Selecione o alerta para notificação", list(opcoes.keys()))
        reg = df_risco.loc[opcoes[selecao]]

        mensagem = gerar_mensagem_alerta(
            reg["Aluno"], reg["Turma/Curso"], reg["Disciplina"],
            reg["Nota"], reg["Frequência (%)"], reg["Risco IA (%)"], reg["Ação Recomendada"]
        )

        col_msg, col_envio = st.columns([3, 2])
        with col_msg:
            assunto = st.text_input("Assunto do comunicado", value=f"EduAlerta | Acompanhamento Acadêmico — {reg['Aluno']}")
            texto_editado = st.text_area("Mensagem pronta (editável para E-mail ou WhatsApp)", value=mensagem, height=260)

        with col_envio:
            st.markdown("#### Canal de Envio")
            destino = st.text_input("E-mail de destino", value=reg["E-mail"])
            if st.button("✉️ Enviar Alerta por E-mail (SMTP)", type="primary", use_container_width=True):
                ok, retorno = enviar_email_alerta(destino, assunto, texto_editado)
                if ok:
                    st.success(retorno)
                else:
                    st.warning(retorno)
            st.caption("Sem SMTP configurado, você pode copiar o texto ao lado e colar diretamente no WhatsApp institucional ou no portal da escola.")

# ==========================================
# 4. SIMULADOR & AUDITORIA DA IA
# ==========================================
elif pagina == "Simulador & Auditoria IA":
    aba_sim, aba_aud = st.tabs(["Simulador Preditivo ao Vivo", "Governança e Métricas do Modelo"])

    with aba_sim:
        col_sim, col_exp = st.columns([3, 2])
        with col_sim:
            st.subheader("Teste de Cenários em Tempo Real")
            s_nota = st.slider("Nota atual (0 a 10)", 0.0, 10.0, 6.2, 0.1)
            s_freq = st.slider("Frequência (%)", 40, 100, 78, 1)
            s_ativ = st.slider("Atividades entregues no AVA/Portal (%)", 0, 100, 35, 5)

            res = prever_risco_ml(modelo_ia, s_nota, s_freq, s_ativ)
            m1, m2 = st.columns(2)
            m1.metric("Probabilidade de Risco (IA)", f"{res['probabilidade']}%")
            m2.metric("Classificação", res["faixa"])

            if res["faixa"] == "ALTO RISCO":
                st.error(f"**Plano de ação recomendado:** {res['recomendacao']}")
            elif res["faixa"] == "RISCO MODERADO":
                st.warning(f"**Plano de ação recomendado:** {res['recomendacao']}")
            else:
                st.success(f"**Situação estável:** {res['recomendacao']}")

        with col_exp:
            st.subheader("Importância das Variáveis")
            fig_imp = px.bar(
                df_importancias, x="Peso (%)", y="Fator", orientation="h",
                text="Peso (%)", template="plotly_white"
            )
            fig_imp.update_layout(height=310, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_imp, use_container_width=True)

    with aba_aud:
        st.subheader("Validação Estatística do Algoritmo Random Forest")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Acurácia", f"{metricas_ia['acuracia']}%")
        m2.metric("Precisão", f"{metricas_ia['precisao']}%")
        m3.metric("Recall (Sensibilidade)", f"{metricas_ia['recall']}%")
        m4.metric("F1-Score", f"{metricas_ia['f1']}%")

        col_cm, col_txt = st.columns([2, 3])
        with col_cm:
            fig_cm = px.imshow(
                matriz_confusao, text_auto=True,
                x=["Prev. Normal", "Prev. Risco"],
                y=["Real Normal", "Real Risco"],
                color_continuous_scale="Blues",
                title="Matriz de Confusão (Base de Teste)"
            )
            fig_cm.update_layout(height=340, coloraxis_showscale=False)
            st.plotly_chart(fig_cm, use_container_width=True)

        with col_txt:
            st.markdown(f"""
            **Por que o Recall é a métrica mais importante aqui?**
            * Em prevenção escolar, deixar passar um aluno em risco (**falso negativo**) custa muito mais caro do que gerar um acompanhamento extra.
            * O modelo foi treinado com **{metricas_ia['amostras_treino']} registros** e validado em **{metricas_ia['amostras_teste']} casos inéditos** (divisão estratificada 80/20).
            * **Hiperparâmetros:** 150 árvores de decisão (`n_estimators=150`), profundidade controlada (`max_depth=8`) para evitar sobreajuste (*overfitting*).
            """)

# ==========================================
# 5. IMPORTADOR INTELIGENTE DO PORTAL
# ==========================================
elif pagina == "Importar do Portal":
    st.subheader("Importador Universal de Portais (TOTVS RM, SIGAA, Moodle, Classroom)")
    st.write("Suba qualquer planilha `.csv` ou `.xlsx` exportada do portal da sua instituição e associe as colunas abaixo — sem precisar editar o arquivo antes.")

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
    buf = io.BytesIO()
    modelo_planilha.to_excel(buf, index=False)
    st.download_button(
        "📄 Baixar Planilha Modelo (.xlsx)",
        data=buf.getvalue(),
        file_name="modelo_importacao_edualerta.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    arquivo = st.file_uploader("Selecione o arquivo exportado do portal (.csv ou .xlsx)", type=["csv", "xlsx"])
    if arquivo:
        try:
            df_up = pd.read_csv(arquivo, sep=None, engine="python") if arquivo.name.endswith(".csv") else pd.read_excel(arquivo)
            st.dataframe(df_up.head(5), use_container_width=True)

            cols = list(df_up.columns)
            cols_opc = ["(Não possui na planilha)"] + cols

            def sugerir(lista, termos):
                for idx, nome_c in enumerate(lista):
                    if any(t in str(nome_c).lower() for t in termos):
                        return idx
                return 0

            st.markdown("#### Mapeamento de Colunas")
            mc1, mc2, mc3 = st.columns(3)
            c_nome = mc1.selectbox("Nome do Aluno *", cols, index=sugerir(cols, ["nome", "aluno", "estudante"]))
            c_mat = mc2.selectbox("Matrícula / RA *", cols, index=sugerir(cols, ["matr", "ra", "registro", "id"]))
            c_turma = mc3.selectbox("Turma / Curso *", cols, index=sugerir(cols, ["turma", "curso", "serie", "série"]))

            mc4, mc5, mc6 = st.columns(3)
            c_disc = mc4.selectbox("Disciplina *", cols, index=sugerir(cols, ["disc", "mater", "matér", "comp"]))
            c_per = mc5.selectbox("Período *", cols, index=sugerir(cols, ["per", "bim", "sem", "etapa"]))
            c_nota = mc6.selectbox("Nota *", cols, index=sugerir(cols, ["nota", "media", "média"]))

            mc7, mc8, mc9 = st.columns(3)
            c_freq = mc7.selectbox("Frequência (%) *", cols, index=sugerir(cols, ["freq", "presen", "falt"]))
            c_ativ = mc8.selectbox("Atividades (%) (opcional)", cols_opc, index=sugerir(cols_opc, ["ativ", "entreg", "ava"]))
            c_email = mc9.selectbox("E-mail (opcional)", cols_opc, index=sugerir(cols_opc, ["mail", "contato"]))

            if st.button("🚀 Importar e Analisar com IA", type="primary"):
                novos, atualizados = 0, 0
                with SessionLocal() as db:
                    for _, row in df_up.iterrows():
                        mat = str(row[c_mat]).strip()
                        aluno = db.query(Aluno).filter(Aluno.matricula == mat).first()
                        if not aluno:
                            aluno = Aluno(
                                nome=str(row[c_nome]).strip(),
                                matricula=mat,
                                turma=str(row[c_turma]).strip(),
                                email_responsavel="" if c_email == "(Não possui na planilha)" else str(row[c_email]).strip()
                            )
                            db.add(aluno)
                            db.flush()

                        disc_v = str(row[c_disc]).strip()
                        per_v = str(row[c_per]).strip()
                        nota_v = limpar_numero(row[c_nota])
                        freq_v = limpar_numero(row[c_freq])
                        ativ_v = 100.0 if c_ativ == "(Não possui na planilha)" else limpar_numero(row[c_ativ], 100.0)

                        reg_ex = db.query(Desempenho).filter(
                            Desempenho.aluno_id == aluno.id,
                            Desempenho.disciplina == disc_v,
                            Desempenho.periodo == per_v
                        ).first()
                        if reg_ex:
                            reg_ex.nota = nota_v
                            reg_ex.frequencia = freq_v
                            reg_ex.atividades = ativ_v
                            atualizados += 1
                        else:
                            db.add(Desempenho(
                                aluno_id=aluno.id, disciplina=disc_v, periodo=per_v,
                                nota=nota_v, frequencia=freq_v, atividades=ativ_v
                            ))
                            novos += 1
                    db.commit()
                st.success(f"Importação concluída: **{novos}** registros novos e **{atualizados}** atualizados (sem duplicidades).")
        except Exception as erro:
            st.error(f"Não foi possível processar a planilha: {erro}")

# ==========================================
# 6. GESTÃO DE CADASTROS (CRUD)
# ==========================================
elif pagina == "Gestão de Cadastros":
    aba1, aba2, aba3 = st.tabs(["Cadastrar Aluno", "Lançar Desempenho", "Gerenciar / Excluir"])

    with aba1:
        with st.form("form_aluno", clear_on_submit=True):
            nome = st.text_input("Nome completo")
            matricula = st.text_input("Matrícula / RA")
            turma = st.text_input("Turma ou Curso (ex.: ADS - 3º Período ou 3º Ano A)")
            email = st.text_input("E-mail do estudante ou responsável")
            if st.form_submit_button("Salvar Aluno", type="primary"):
                if nome and matricula and turma:
                    try:
                        with SessionLocal() as db:
                            db.add(Aluno(nome=nome.strip(), matricula=matricula.strip(), turma=turma.strip(), email_responsavel=email.strip()))
                            db.commit()
                        st.success("Estudante cadastrado com sucesso.")
                    except IntegrityError:
                        st.error("Já existe um estudante com essa matrícula.")
                else:
                    st.warning("Preencha nome, matrícula e turma/curso.")

    with aba2:
        with SessionLocal() as db:
            alunos = db.query(Aluno).order_by(Aluno.nome).all()
        if not alunos:
            st.info("Cadastre ao menos um aluno antes de registrar desempenho.")
        else:
            mapa = {f"{a.nome} ({a.matricula})": a.id for a in alunos}
            with st.form("form_desempenho", clear_on_submit=True):
                aluno_sel = st.selectbox("Estudante", list(mapa.keys()))
                disciplina = st.text_input("Disciplina")
                periodo = st.selectbox("Período", ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre", "1º Semestre", "2º Semestre"])
                nota = st.number_input("Nota (0 a 10)", 0.0, 10.0, 7.0, 0.5)
                frequencia = st.number_input("Frequência (%)", 0.0, 100.0, 90.0, 1.0)
                atividades = st.number_input("Atividades entregues (%)", 0.0, 100.0, 80.0, 5.0)
                if st.form_submit_button("Registrar Desempenho", type="primary"):
                    if disciplina.strip():
                        with SessionLocal() as db:
                            db.add(Desempenho(
                                aluno_id=mapa[aluno_sel], disciplina=disciplina.strip(), periodo=periodo,
                                nota=nota, frequencia=frequencia, atividades=atividades
                            ))
                            db.commit()
                        st.success("Lançamento registrado e processado pela IA.")
                    else:
                        st.warning("Informe o nome da disciplina.")

    with aba3:
        st.subheader("Remover Estudante (e respectivos lançamentos)")
        with SessionLocal() as db:
            alunos = db.query(Aluno).order_by(Aluno.nome).all()
        if not alunos:
            st.info("Nenhum aluno cadastrado.")
        else:
            mapa_del = {f"{a.nome} — Matrícula {a.matricula} ({a.turma})": a.id for a in alunos}
            escolhido = st.selectbox("Selecione o estudante para excluir", list(mapa_del.keys()))
            if st.button("🗑️ Excluir Estudante Selecionado"):
                with SessionLocal() as db:
                    alvo = db.query(Aluno).filter(Aluno.id == mapa_del[escolhido]).first()
                    if alvo:
                        db.delete(alvo)
                        db.commit()
                st.success("Registro removido do banco de dados.")
                st.rerun()

# ==========================================
# 7. INTEGRAR EM PORTAIS
# ==========================================
elif pagina == "Integrar em Portais":
    st.subheader("1. Incorporação Direta no Portal Acadêmico (Iframe HTTPS)")
    st.write("Cole o código abaixo no **Moodle**, **Google Sites**, **WordPress** ou na **Intranet da Escola/Faculdade**. O parâmetro `?embed=true` oculta o banner superior automaticamente para encaixar melhor no portal:")
    st.code(
        '<iframe src="https://edualerta.streamlit.app/?embed=true" width="100%" height="860" style="border:none; border-radius:12px;"></iframe>',
        language="html"
    )

    st.subheader("2. Padrão de Contrato JSON para Integração Automática (API / Webhook)")
    st.write("Para faculdades com TI interna (TOTVS RM, Lyceum, SIGAA ou SUAP), o envio automático de eventos ao banco PostgreSQL segue este contrato REST:")
    st.code("""{
  "instituicao_id": "UNIDADE-01",
  "matricula": "2026102",
  "nome": "Bruno Henrique Costa",
  "turma": "ADS - 2º Período",
  "disciplina": "Algoritmos",
  "periodo": "1º Semestre",
  "nota": 6.4,
  "frequencia": 80.0,
  "atividades_entregues": 35.0
}""", language="json")

    st.subheader("3. Configuração Opcional de Segurança e E-mail (Secrets)")
    st.code("""DATABASE_URL = "postgresql+psycopg://..."
ADMIN_USER = "coordenacao"
ADMIN_PASSWORD = "sua_senha_institucional"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = "587"
SMTP_USER = "alertas@suainstituicao.edu.br"
SMTP_PASSWORD = "senha_de_app_smtp" """, language="toml")
