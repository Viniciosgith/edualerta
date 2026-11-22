def avaliar_risco(nota: float, frequencia: float) -> dict:
    """Classifica o desempenho escolar em Normal, Atenção ou Crítico."""
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