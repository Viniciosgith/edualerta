import os
import streamlit as st
from database import inicializar_banco
from modelo_ml import treinar_modelo
from services import carregar_desempenho
from views import visao_geral, estudantes, ia, gestao

st.set_page_config(page_title="EduAlerta", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; max-width: 1280px; }
    h1 { font-size: 1.75rem !important; font-weight: 700 !important; letter-spacing: -0.02em; }
    [data-testid="stMetricValue"] { font-size: 1.65rem !important; font-weight: 600 !important; }
    [data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.85rem !important; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def setup():
    inicializar_banco()
    return treinar_modelo()


modelo_ia, metricas_ia, matriz_confusao, df_importancias = setup()

ADMIN_USER = os.getenv("ADMIN_USER", "coordenacao")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "edualerta2026")
MODO_EMBED = st.query_params.get("embed") == "true"

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = MODO_EMBED

if not st.session_state["autenticado"]:
    _, centro, _ = st.columns([1.2, 1.2, 1.2])
    with centro:
        st.markdown("<div style='height: 6vh'></div>", unsafe_allow_html=True)
        with st.form("login", border=True):
            st.subheader("EduAlerta")
            st.caption("Acesso institucional à plataforma de desempenho acadêmico.")
            usuario = st.text_input("Usuário", placeholder="coordenacao")
            senha = st.text_input("Senha", type="password", placeholder="••••••••")
            if st.form_submit_button("Entrar", type="primary", use_container_width=True):
                if usuario.strip() == ADMIN_USER and senha == ADMIN_PASSWORD:
                    st.session_state["autenticado"] = True
                    st.rerun()
                st.error("Credenciais inválidas.")
        st.caption("Demonstração: `coordenacao` / `edualerta2026`")
    st.stop()

with st.sidebar:
    import os
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown("### EduAlerta")
        st.caption("Learning Analytics")

navegacao = st.navigation([
    st.Page(pg_visao_geral, title="Visão Geral", icon=":material/dashboard:"),
    st.Page(pg_estudantes, title="Estudantes", icon=":material/group:"),
    st.Page(pg_ia, title="IA Preditiva", icon=":material/analytics:"),
    st.Page(pg_gestao, title="Gestão e Portais", icon=":material/settings:"),
])

if not MODO_EMBED:
    with st.sidebar:
        st.divider()
        st.caption(f"Modelo Random Forest · F1 {metricas_ia['f1']}%")
        if st.button("Sair", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()

navegacao.run()
