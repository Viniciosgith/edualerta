import hmac
import os
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image
import streamlit as st
from database import inicializar_banco
from modelo_ml import treinar_modelo
from services import carregar_desempenho
from views import visao_geral, estudantes, ia, gestao

st.set_page_config(page_title="EduAlerta", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; max-width: 1280px; }
    h1 { font-size: 1.75rem !important; font-weight: 700 !important; letter-spacing: -0.02em; }
    [data-testid="stMetricValue"] { font-size: 1.65rem !important; font-weight: 600 !important; }
    [data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.85rem !important; }
    [data-testid="stLogo"] { height: 2.3rem !important; width: auto !important; }
    .top-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 0.75rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid #e2e8f0;
        color: #64748b;
        font-size: 0.85rem;
    }
    .top-bar strong { color: #0f172a; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


def obter_logo() -> str | None:
    pasta = Path(__file__).resolve().parent
    extensoes = (".png", ".jpg", ".jpeg", ".webp")
    for arquivo in pasta.iterdir():
        if arquivo.is_file() and arquivo.suffix.lower() in extensoes and "logo" in arquivo.name.lower():
            return str(arquivo)
    return None


@st.cache_resource
def preparar_logo(caminho: str) -> str:
    img = Image.open(caminho).convert("RGBA")
    arr = np.array(img)
    fundo_branco = (arr[:, :, 0] > 235) & (arr[:, :, 1] > 235) & (arr[:, :, 2] > 235)
    arr[fundo_branco, 3] = 0
    img_limpa = Image.fromarray(arr)
    bbox = img_limpa.getbbox()
    if bbox:
        img_limpa = img_limpa.crop(bbox)
    destino = Path(tempfile.gettempdir()) / "edualerta_logo_limpo.png"
    img_limpa.save(destino, format="PNG")
    return str(destino)


@st.cache_resource
def setup():
    inicializar_banco()
    return treinar_modelo()


modelo_ia, metricas_ia, matriz_confusao, df_importancias = setup()
arquivo_logo = obter_logo()
caminho_logo = preparar_logo(arquivo_logo) if arquivo_logo else None

ADMIN_USER = os.getenv("ADMIN_USER", "coordenacao")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "edualerta2026")
EMBED_TOKEN = os.getenv("EMBED_TOKEN", "")
USANDO_SENHA_DEMO = ADMIN_PASSWORD == "edualerta2026"

token_url = st.query_params.get("token", "")
MODO_EMBED = (
    st.query_params.get("embed") == "true"
    and bool(EMBED_TOKEN)
    and hmac.compare_digest(token_url, EMBED_TOKEN)
)

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = MODO_EMBED

if not st.session_state["autenticado"]:
    _, centro, _ = st.columns([1.2, 1.2, 1.2])
    with centro:
        st.markdown("<div style='height: 6vh'></div>", unsafe_allow_html=True)
        with st.form("login", border=True):
            if caminho_logo:
                st.image(caminho_logo, width=220)
            else:
                st.subheader("EduAlerta")
            st.caption("Acesso institucional à plataforma de desempenho acadêmico.")
            usuario = st.text_input("Usuário", placeholder="coordenacao")
            senha = st.text_input("Senha", type="password", placeholder="••••••••")
            if st.form_submit_button("Entrar", type="primary", use_container_width=True):
                user_ok = hmac.compare_digest(usuario.strip(), ADMIN_USER)
                pass_ok = hmac.compare_digest(senha, ADMIN_PASSWORD)
                if user_ok and pass_ok:
                    st.session_state["autenticado"] = True
                    st.rerun()
                st.error("Credenciais inválidas.")
        if USANDO_SENHA_DEMO:
            st.caption("Demonstração: `coordenacao` / `edualerta2026`")
    st.stop()

if caminho_logo:
    st.logo(caminho_logo, size="large")

with st.sidebar:
    modo_lgpd = st.toggle(
        "Modo LGPD (Anonimizado)",
        value=False,
        help="Oculta nomes, matrículas e e-mails para apresentações e reuniões.",
    )


def pg_visao_geral():
    visao_geral.render(carregar_desempenho(modelo_ia, anonimizar=modo_lgpd), modo_lgpd=modo_lgpd)


def pg_estudantes():
    estudantes.render(carregar_desempenho(modelo_ia, anonimizar=modo_lgpd), modo_lgpd=modo_lgpd)


def pg_ia():
    ia.render(modelo_ia, metricas_ia, matriz_confusao, df_importancias)


def pg_gestao():
    gestao.render()


navegacao = st.navigation([
    st.Page(pg_visao_geral, title="Visão Geral", icon=":material/dashboard:"),
    st.Page(pg_estudantes, title="Estudantes", icon=":material/group:"),
    st.Page(pg_ia, title="IA Preditiva", icon=":material/analytics:"),
    st.Page(pg_gestao, title="Gestão e Portais", icon=":material/settings:"),
])

if not MODO_EMBED:
    badge_lgpd = " · Modo LGPD ativo" if modo_lgpd else ""
    st.markdown(
        f'<div class="top-bar">'
        f'<span><strong>EduAlerta</strong> · Controle e Alerta de Desempenho Escolar{badge_lgpd}</span>'
        f'<span>Random Forest · F1 {metricas_ia["f1"]}%</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    with st.sidebar:
        st.divider()
        if st.button("Sair", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()

navegacao.run()
