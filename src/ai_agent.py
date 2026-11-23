from src.database import SessionLocal, LogAlerta


class AgenteRetencaoIA:
    """Agente autônomo que interpreta o risco do modelo de ML e orquestra alertas."""

    def definir_estrategia(self, diagnostico: str, probabilidade: float) -> dict:
        if diagnostico == "Risco de Evasão":
            return {
                "prioridade": "CRÍTICA",
                "setor": "Coordenação + Núcleo de Apoio (NAE)",
                "acao": "Contato ativo em até 24h, plano de recuperação e escuta ativa.",
            }
        if diagnostico == "Risco de Trancamento":
            return {
                "prioridade": "ALTA",
                "setor": "Coordenação + Setor Financeiro",
                "acao": "Oferecer renegociação, bolsa emergencial ou ajuste de grade.",
            }
        if diagnostico == "Risco de Mudança de Curso":
            return {
                "prioridade": "MODERADA",
                "setor": "Coordenação + Orientação Vocacional",
                "acao": "Agendar conversa de carreira e avaliar aproveitamento de disciplinas.",
            }
        return {
            "prioridade": "BAIXA",
            "setor": "Monitoramento passivo",
            "acao": "Manter acompanhamento regular sem disparo emergencial.",
        }

    def gerar_alertas(self, aluno: dict, resultado_ml: dict) -> dict:
        diag = resultado_ml["diagnostico"]
        prob = resultado_ml["probabilidade"]
        fatores_txt = "; ".join(resultado_ml["fatores"])
        estrategia = self.definir_estrategia(diag, prob)

        # 1. Alerta técnico para a Coordenação
        msg_coordenacao = (
            f"[ALERTA {estrategia['prioridade']} — {diag.upper()}]\n"
            f"Estudante: {aluno['nome']} (Matrícula: {aluno['matricula']})\n"
            f"Curso/Semestre: {aluno['curso']} — {aluno['semestre']}º semestre\n"
            f"Confiança do Modelo ML: {prob}%\n"
            f"Principais gatilhos: {fatores_txt}\n"
            f"Setor recomendado: {estrategia['setor']}\n"
            f"Ação sugerida: {estrategia['acao']}"
        )

        # 2. Alerta empático e personalizado para o Aluno
        if diag == "Risco de Evasão":
            msg_aluno = (
                f"Olá, {aluno['nome'].split()[0]}! Tudo bem?\n\n"
                f"Notamos que as últimas semanas em {aluno['curso']} podem ter sido mais puxadas "
                f"e queremos reforçar que você não precisa passar por isso sozinho(a). "
                f"Nossa equipe de monitoria e a coordenação estão disponíveis para montar um plano leve "
                f"de recuperação com você. Podemos agendar uma conversa rápida esta semana?"
            )
        elif diag == "Risco de Trancamento":
            msg_aluno = (
                f"Olá, {aluno['nome'].split()[0]}! Como você está?\n\n"
                f"Sabemos que conciliar faculdade, rotina e questões financeiras nem sempre é simples. "
                f"Antes de pensar em pausar o curso de {aluno['curso']}, saiba que temos opções de "
                f"flexibilização de grade e renegociação que podem te ajudar a continuar. Vamos conversar?"
            )
        elif diag == "Risco de Mudança de Curso":
            msg_aluno = (
                f"Olá, {aluno['nome'].split()[0]}!\n\n"
                f"Vimos que você tem um bom desempenho em {aluno['curso']}, mas percebemos que talvez "
                f"o curso não esteja totalmente alinhado com o que você busca hoje. Que tal um bate-papo "
                f"com nossa orientação de carreira para explorar projetos, trilhas ou até opções internas?"
            )
        else:
            msg_aluno = (
                f"Olá, {aluno['nome'].split()[0]}! Parabéns pelo seu ritmo em {aluno['curso']}. "
                f"Continue contando com a coordenação para potencializar sua jornada acadêmica."
            )

        return {
            "prioridade": estrategia["prioridade"],
            "setor": estrategia["setor"],
            "acao": estrategia["acao"],
            "msg_coordenacao": msg_coordenacao,
            "msg_aluno": msg_aluno,
        }

    def disparar_e_registrar(self, aluno_id: int, resultado_ml: dict, pacote_alertas: dict) -> None:
        with SessionLocal() as db:
            log = LogAlerta(
                aluno_id=aluno_id,
                diagnostico_ml=resultado_ml["diagnostico"],
                probabilidade=resultado_ml["probabilidade"],
                prioridade=pacote_alertas["prioridade"],
                msg_coordenacao=pacote_alertas["msg_coordenacao"],
                msg_aluno=pacote_alertas["msg_aluno"],
                status_envio="Disparado (Coordenação + Aluno)",
            )
            db.add(log)
            db.commit()
