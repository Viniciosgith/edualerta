import os
import smtplib
from email.message import EmailMessage

def avaliar_risco(nota: float, frequencia: float) -> dict:
    """Classifica o desempenho escolar em NORMAL, ATENÇÃO ou CRÍTICO."""
    motivos = []
    nivel = "NORMAL"

    if nota < 5.0:
        nivel = "CRÍTICO"
        motivos.append(f"Nota crítica ({nota:.1f})")
    elif nota < 7.0:
        nivel = "ATENÇÃO"
        motivos.append(f"Nota abaixo da média ({nota:.1f})")

    if frequencia < 75.0:
        nivel = "CRÍTICO"
        motivos.append(f"Frequência abaixo do mínimo legal ({frequencia:.0f}%)")
    elif frequencia < 85.0 and nivel == "NORMAL":
        nivel = "ATENÇÃO"
        motivos.append(f"Queda de frequência ({frequencia:.0f}%)")

    return {
        "nivel": nivel,
        "motivo": " | ".join(motivos) if motivos else "Desempenho adequado"
    }

def gerar_mensagem_alerta(nome: str, turma: str, disciplina: str, nota: float, frequencia: float, risco_ia: float, recomendacao: str) -> str:
    """Gera texto institucional pronto para envio por e-mail ou WhatsApp."""
    return (
        f"Prezado(a),\n\n"
        f"Informamos que nosso sistema de acompanhamento acadêmico (EduAlerta) identificou um sinal de atenção "
        f"no desempenho de {nome} ({turma}) na disciplina de {disciplina}:\n\n"
        f"- Nota registrada: {nota:.1f}\n"
        f"- Frequência atual: {frequencia:.0f}%\n"
        f"- Índice preditivo de risco: {risco_ia:.1f}%\n\n"
        f"Encaminhamento sugerido: {recomendacao}.\n\n"
        f"Solicitamos o contato com a Coordenação Pedagógica para alinharmos o plano de apoio ao estudante.\n\n"
        f"Atenciosamente,\n"
        f"Coordenação Acadêmica — EduAlerta"
    )

def enviar_email_alerta(destinatario: str, assunto: str, corpo: str) -> tuple[bool, str]:
    """Dispara e-mail real via SMTP caso as variáveis SMTP estejam configuradas nos Secrets."""
    servidor = os.getenv("SMTP_SERVER")
    porta = int(os.getenv("SMTP_PORT", "587"))
    usuario = os.getenv("SMTP_USER")
    senha = os.getenv("SMTP_PASSWORD")

    if not all([servidor, usuario, senha]):
        return False, "SMTP não configurado nos Secrets (adicione SMTP_SERVER, SMTP_USER e SMTP_PASSWORD para disparo real)."

    if not destinatario or "@" not in destinatario:
        return False, "E-mail do destinatário inválido ou não cadastrado."

    try:
        msg = EmailMessage()
        msg["Subject"] = assunto
        msg["From"] = usuario
        msg["To"] = destinatario
        msg.set_content(corpo)

        with smtplib.SMTP(servidor, porta, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(usuario, senha)
            smtp.send_message(msg)
        return True, f"Alerta enviado com sucesso para {destinatario}."
    except Exception as e:
        return False, f"Falha no envio SMTP: {e}"
