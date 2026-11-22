import io
import pandas as pd
import streamlit as st
from services import (
    listar_alunos, listar_lancamentos_simples, cadastrar_aluno, excluir_aluno,
    registrar_desempenho, atualizar_desempenho, excluir_desempenho,
    importar_planilha, popular_dados_demo, higienizar_base,
)

PERIODOS = ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre", "1º Semestre", "2º Semestre"]


def _sugerir_indice(lista: list[str], termos: list[str]) -> int:
    for idx, nome in enumerate(lista):
        if any(t in str(nome).lower() for t in termos):
            return idx
    return 0


def render():
    st.title("Gestão e Portais")
    st.caption("Importação validada de planilhas, manutenção de registros e incorporação segura.")

    aba_imp, aba_cad, aba_base, aba_portal = st.tabs([
        "Importar Planilha", "Cadastros", "Gerenciar Base", "Integrar em Portais"
    ])

    with aba_imp:
        modelo = pd.DataFrame([
            {
                "nome": "Lucas Pereira", "matricula": "2026901", "turma": "ADS - 1º Período",
                "email_responsavel": "lucas@faculdade.edu", "disciplina": "Programação Web",
                "periodo": "1º Semestre", "nota": 6.0, "frequencia": 74, "atividades": 40,
            }
        ])
        buf = io.BytesIO()
        modelo.to_excel(buf, index=False)

        col_txt, col_dl = st.columns([4, 1.5], vertical_alignment="center")
        col_txt.write("Compatível com `.csv` ou `.xlsx` do TOTVS RM, SIGAA, Moodle e Google Classroom. Disciplinas são padronizadas automaticamente.")
        col_dl.download_button(
            "Baixar modelo .xlsx", data=buf.getvalue(),
            file_name="modelo_edualerta.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        arquivo = st.file_uploader("Enviar planilha", type=["csv", "xlsx"])
        if arquivo:
            try:
                df_up = pd.read_csv(arquivo, sep=None, engine="python") if arquivo.name.endswith(".csv") else pd.read_excel(arquivo)
                st.dataframe(df_up.head(5), use_container_width=True, hide_index=True)

                cols = list(df_up.columns)
                cols_opc = ["(Opcional / ausente)"] + cols

                with st.container(border=True):
                    st.markdown("**Mapeamento de colunas**")
                    r1 = st.columns(3)
                    c_nome = r1[0].selectbox("Nome", cols, index=_sugerir_indice(cols, ["nome", "aluno"]))
                    c_mat = r1[1].selectbox("Matrícula / RA", cols, index=_sugerir_indice(cols, ["matr", "ra", "id"]))
                    c_turma = r1[2].selectbox("Turma / Curso", cols, index=_sugerir_indice(cols, ["turma", "curso", "série"]))

                    r2 = st.columns(3)
                    c_disc = r2[0].selectbox("Disciplina", cols, index=_sugerir_indice(cols, ["disc", "matér", "mater"]))
                    c_per = r2[1].selectbox("Período", cols, index=_sugerir_indice(cols, ["per", "bim", "sem"]))
                    c_nota = r2[2].selectbox("Nota", cols, index=_sugerir_indice(cols, ["nota", "média", "media"]))

                    r3 = st.columns(3)
                    c_freq = r3[0].selectbox("Frequência (%)", cols, index=_sugerir_indice(cols, ["freq", "presen"]))
                    c_ativ = r3[1].selectbox("Atividades (%)", cols_opc, index=_sugerir_indice(cols_opc, ["ativ", "entreg"]))
                    c_email = r3[2].selectbox("E-mail", cols_opc, index=_sugerir_indice(cols_opc, ["mail"]))

                    if st.button("Importar registros", type="primary"):
                        mapa = {
                            "nome": c_nome, "matricula": c_mat, "turma": c_turma,
                            "disciplina": c_disc, "periodo": c_per, "nota": c_nota,
                            "frequencia": c_freq,
                            "atividades": None if c_ativ == "(Opcional / ausente)" else c_ativ,
                            "email": None if c_email == "(Opcional / ausente)" else c_email,
                        }
                        novos, atualizados, ignorados = importar_planilha(df_up, mapa)
                        st.success(f"Concluído: {novos} novos, {atualizados} atualizados e {ignorados} inválidos ignorados.")
            except Exception as err:
                st.error(f"Erro ao ler arquivo: {err}")

    with aba_cad:
        c_aluno, c_nota = st.columns(2)
        with c_aluno:
            with st.form("form_aluno", clear_on_submit=True, border=True):
                st.markdown("**Novo Estudante**")
                nome = st.text_input("Nome completo")
                mat = st.text_input("Matrícula / RA")
                turma = st.text_input("Turma ou Curso")
                email = st.text_input("E-mail")
                if st.form_submit_button("Salvar estudante", type="primary", use_container_width=True):
                    ok, msg = cadastrar_aluno(nome, mat, turma, email)
                    st.success(msg) if ok else st.error(msg)

        with c_nota:
            alunos = listar_alunos()
            with st.form("form_desempenho", clear_on_submit=True, border=True):
                st.markdown("**Lançar Desempenho**")
                if not alunos:
                    st.info("Cadastre ao menos um estudante primeiro.")
                    st.form_submit_button("Registrar", disabled=True)
                else:
                    mapa = {f"{a['nome']} ({a['matricula']})": a["id"] for a in alunos}
                    sel = st.selectbox("Estudante", list(mapa.keys()))
                    disc = st.text_input("Disciplina")
                    per = st.selectbox("Período", PERIODOS)
                    n1, n2, n3 = st.columns(3)
                    nota = n1.number_input("Nota", 0.0, 10.0, 7.0, 0.5)
                    freq = n2.number_input("Freq. (%)", 0.0, 100.0, 90.0, 1.0)
                    ativ = n3.number_input("Ativ. (%)", 0.0, 100.0, 80.0, 5.0)
                    if st.form_submit_button("Registrar desempenho", type="primary", use_container_width=True):
                        ok, msg = registrar_desempenho(mapa[sel], disc, per, nota, freq, ativ)
                        st.success(msg) if ok else st.warning(msg)

    with aba_base:
        col_edit, col_manut = st.columns([3, 2])

        with col_edit:
            with st.container(border=True):
                st.markdown("**Editar ou Excluir Lançamento Individual**")
                lancs = listar_lancamentos_simples()
                if not lancs:
                    st.info("Nenhum lançamento cadastrado.")
                else:
                    mapa_l = {
                        f"#{l['id']} · {l['aluno']} — {l['disciplina']} ({l['periodo']}) | Nota {l['nota']:.1f}": l
                        for l in lancs
                    }
                    sel_l = st.selectbox("Selecionar lançamento", list(mapa_l.keys()))
                    item = mapa_l[sel_l]
                    with st.form("form_editar_lanc"):
                        e_disc = st.text_input("Disciplina", value="" if item["disciplina"] == "(vazio)" else item["disciplina"])
                        idx_per = PERIODOS.index(item["periodo"]) if item["periodo"] in PERIODOS else 0
                        e_per = st.selectbox("Período", PERIODOS, index=idx_per)
                        ec1, ec2, ec3 = st.columns(3)
                        e_nota = ec1.number_input("Nota", 0.0, 10.0, min(max(item["nota"], 0.0), 10.0), 0.5)
                        e_freq = ec2.number_input("Freq. (%)", 0.0, 100.0, min(max(item["frequencia"], 0.0), 100.0), 1.0)
                        e_ativ = ec3.number_input("Ativ. (%)", 0.0, 100.0, min(max(item["atividades"], 0.0), 100.0), 5.0)
                        b1, b2 = st.columns(2)
                        salvar_ed = b1.form_submit_button("Salvar alteração", type="primary", use_container_width=True)
                        excluir_ed = b2.form_submit_button("Excluir lançamento", use_container_width=True)

                        if salvar_ed:
                            ok, msg = atualizar_desempenho(item["id"], e_disc, e_per, e_nota, e_freq, e_ativ)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.warning(msg)
                        if excluir_ed:
                            excluir_desempenho(item["id"])
                            st.success("Lançamento excluído.")
                            st.rerun()

        with col_manut:
            with st.container(border=True):
                st.markdown("**Higienização e Demonstração**")
                st.caption("Padroniza nomes de disciplinas (ex.: MATEMATICA → Matemática) e remove registros vazios.")
                if st.button("Higienizar base agora", type="primary", use_container_width=True):
                    rem, pad = higienizar_base()
                    st.success(f"Limpeza concluída: {rem} vazios removidos e {pad} padronizados.")
                    if rem or pad:
                        st.rerun()
                if st.button("Carregar base demonstrativa", use_container_width=True):
                    qtd = popular_dados_demo()
                    st.success(f"{qtd} registros inseridos.") if qtd else st.info("A base demonstrativa já existe.")

            with st.container(border=True):
                st.markdown("**Remover Estudante (e histórico)**")
                alunos = listar_alunos()
                if not alunos:
                    st.info("Nenhum estudante cadastrado.")
                else:
                    mapa = {f"{a['nome']} — {a['matricula']} ({a['turma']})": a["id"] for a in alunos}
                    alvo = st.selectbox("Estudante", list(mapa.keys()))
                    if st.button("Excluir estudante", use_container_width=True):
                        excluir_aluno(mapa[alvo])
                        st.success("Estudante removido.")
                        st.rerun()

    with aba_portal:
        with st.container(border=True):
            st.markdown("**1. Incorporação Segura via Iframe (Moodle, Google Sites, Intranet)**")
            st.caption("Defina `EMBED_TOKEN` nos Secrets do Streamlit Cloud para habilitar o acesso incorporado sem expor o link público.")
            st.code(
                '<iframe src="https://edualerta.streamlit.app/?embed=true&token=SEU_EMBED_TOKEN" width="100%" height="860" style="border:none;"></iframe>',
                language="html",
            )
            st.markdown("**2. Contrato JSON para Integração via API / Webhook**")
            st.code(
                '{\n  "matricula": "2026102",\n  "nome": "Bruno Henrique Costa",\n  "turma": "ADS - 2º Período",\n  "disciplina": "Algoritmos",\n  "periodo": "1º Semestre",\n  "nota": 6.4,\n  "frequencia": 80.0,\n  "atividades": 35.0\n}',
                language="json",
            )
