import pandas as pd
import plotly.express as px
import streamlit as st
from alertas import gerar_mensagem_alerta, enviar_email_alerta
from services import listar_intervencoes, registrar_intervencao, atualizar_intervencao


def render(df, modo_lgpd: bool = False):
    st.title("Estudantes")
    st.caption("Prontuário individual, ciclo de intervenções e comunicação direta.")

    if df.empty:
        st.info("Cadastre ou importe estudantes em **Gestão e Portais** para consultar prontuários.")
        return

    aluno_sel = st.selectbox("Selecionar estudante", sorted(df["Aluno"].unique()), label_visibility="collapsed")
    df_a = df[df["Aluno"] == aluno_sel]
    aluno_id = int(df_a["aluno_id"].iloc[0])
    turma = df_a["Turma"].iloc[0]
    media_turma = df[df["Turma"] == turma]["Nota"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.container(border=True).metric("Turma / Curso", turma)
    c2.container(border=True).metric("Média", f"{df_a['Nota'].mean():.1f}", delta=f"{df_a['Nota'].mean() - media_turma:+.1f} vs turma")
    c3.container(border=True).metric("Frequência", f"{df_a['Frequência (%)'].mean():.0f}%")
    c4.container(border=True).metric("Pico de Risco IA", f"{df_a['Risco IA (%)'].max():.1f}%")

    aba_desemp, aba_int, aba_notif = st.tabs(["Desempenho", "Intervenções", "Notificar"])

    with aba_desemp:
        with st.container(border=True):
            fig = px.bar(df_a, x="Disciplina", y="Nota", color="Período", barmode="group", template="plotly_white")
            fig.add_hline(y=7.0, line_dash="dot", line_color="#16a34a")
            fig.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            df_a[["Disciplina", "Período", "Nota", "Frequência (%)", "Atividades (%)", "Classificação", "Recomendação"]],
            use_container_width=True,
            hide_index=True,
        )

    with aba_int:
        col_hist, col_form = st.columns([3, 2])
        acoes = listar_intervencoes(aluno_id)

        with col_hist:
            if not acoes:
                st.info("Nenhuma intervenção registrada para este estudante.")
            else:
                df_acoes = pd.DataFrame(acoes).drop(columns=["id"])
                st.dataframe(df_acoes, use_container_width=True, hide_index=True)

                with st.form("form_atualizar_intervencao", border=True):
                    st.markdown("**Atualizar status de intervenção existente**")
                    mapa_acoes = {
                        f"#{a['id']} · {a['Tipo']} ({a['Status']}) — {a['Data']}": a
                        for a in acoes
                    }
                    sel_acao = st.selectbox("Intervenção", list(mapa_acoes.keys()))
                    acao_obj = mapa_acoes[sel_acao]
                    lista_status = ["Pendente", "Em andamento", "Concluído"]
                    idx_atual = lista_status.index(acao_obj["Status"]) if acao_obj["Status"] in lista_status else 0
                    novo_status = st.selectbox("Novo status", lista_status, index=idx_atual)
                    nova_obs = st.text_input("Nota de acompanhamento / desfecho", placeholder="Ex.: Responsável compareceu e aluno iniciou monitoria")
                    if st.form_submit_button("Atualizar status", use_container_width=True):
                        atualizar_intervencao(acao_obj["id"], novo_status, nova_obs)
                        st.success("Status atualizado.")
                        st.rerun()

        with col_form:
            with st.form("form_intervencao", clear_on_submit=True, border=True):
                st.markdown("**Nova intervenção**")
                tipo = st.selectbox("Ação", [
                    "Contato com responsável / estudante",
                    "Encaminhamento para monitoria",
                    "Reunião pedagógica",
                    "Plano de recuperação",
                    "Apoio psicopedagógico (NAE)",
                ])
                resp = st.text_input("Responsável", value="Coordenação Pedagógica")
                status = st.selectbox("Status inicial", ["Pendente", "Em andamento", "Concluído"])
                obs = st.text_area("Observações", height=80)
                if st.form_submit_button("Registrar ação", type="primary", use_container_width=True):
                    registrar_intervencao(aluno_id, tipo, resp, status, obs)
                    st.success("Intervenção registrada.")
                    st.rerun()

    with aba_notif:
        if modo_lgpd:
            st.warning("Desative o **Modo LGPD** no menu lateral para visualizar dados nominais e enviar notificações.")
            return

        pior = df_a.sort_values("Risco IA (%)", ascending=False).iloc[0]
        msg = gerar_mensagem_alerta(
            pior["Aluno"], pior["Turma"], pior["Disciplina"],
            pior["Nota"], pior["Frequência (%)"], pior["Risco IA (%)"], pior["Recomendação"],
        )
        col_msg, col_env = st.columns([3, 2])
        with col_msg:
            assunto = st.text_input("Assunto", value=f"EduAlerta | Acompanhamento — {pior['Aluno']}")
            corpo = st.text_area("Mensagem (editável para e-mail ou WhatsApp)", value=msg, height=230)
        with col_env:
            with st.container(border=True):
                destino = st.text_input("E-mail do destinatário", value=pior["E-mail"])
                if st.button("Enviar por e-mail", type="primary", use_container_width=True):
                    ok, retorno = enviar_email_alerta(destino, assunto, corpo)
                    st.success(retorno) if ok else st.warning(retorno)
                st.caption("Sem SMTP configurado, copie o texto ao lado para envio manual via WhatsApp ou portal.")
