import unicodedata
import pandas as pd
from sqlalchemy.exc import IntegrityError
from database import SessionLocal, Aluno, Desempenho, Intervencao
from alertas import avaliar_risco
from modelo_ml import prever_risco_ml

DISCIPLINAS_PADRAO = {
    "matematica": "Matemática",
    "fisica": "Física",
    "quimica": "Química",
    "portugues": "Português",
    "lingua portuguesa": "Língua Portuguesa",
    "historia": "História",
    "geografia": "Geografia",
    "biologia": "Biologia",
    "ingles": "Inglês",
    "calculo i": "Cálculo I",
    "calculo ii": "Cálculo II",
    "calculo 1": "Cálculo I",
    "calculo 2": "Cálculo II",
    "programacao web": "Programação Web",
    "logica de programacao": "Lógica de Programação",
    "inteligencia artificial": "Inteligência Artificial",
    "estatistica": "Estatística",
    "banco de dados": "Banco de Dados",
    "algoritmos": "Algoritmos",
}

PREPOSICOES = {"de", "da", "do", "das", "dos", "e", "em", "para"}
SIGLAS_ROMANOS = {"i", "ii", "iii", "iv", "v", "ia", "bd", "sql", "poo", "ti", "ads"}


def _sem_acentos(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_disciplina(nome: str) -> str:
    if nome is None or (isinstance(nome, float) and pd.isna(nome)):
        return ""
    limpo = " ".join(str(nome).strip().split())
    if not limpo:
        return ""
    chave = _sem_acentos(limpo).lower()
    if chave in DISCIPLINAS_PADRAO:
        return DISCIPLINAS_PADRAO[chave]

    palavras = []
    for idx, palavra in enumerate(limpo.split()):
        low = palavra.lower()
        if low in SIGLAS_ROMANOS:
            palavras.append(palavra.upper())
        elif idx > 0 and low in PREPOSICOES:
            palavras.append(low)
        else:
            palavras.append(palavra.capitalize())
    return " ".join(palavras)


def validar_desempenho(disciplina: str, nota: float, freq: float, ativ: float) -> tuple[bool, str]:
    if not normalizar_disciplina(disciplina):
        return False, "Informe o nome da disciplina."
    if not (0.0 <= nota <= 10.0):
        return False, "A nota deve estar entre 0 e 10."
    if not (0.0 <= freq <= 100.0):
        return False, "A frequência deve estar entre 0% e 100%."
    if not (0.0 <= ativ <= 100.0):
        return False, "As atividades entregues devem estar entre 0% e 100%."
    return True, ""


def limpar_numero(valor, padrao: float = 0.0) -> float:
    if pd.isna(valor):
        return padrao
    try:
        return float(str(valor).replace(",", ".").replace("%", "").strip())
    except ValueError:
        return padrao


def anonimizar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df_mask = df.copy()
    ids_ordenados = sorted(df_mask["aluno_id"].unique())
    mapa_nomes = {aid: f"Estudante #{idx + 1:03d}" for idx, aid in enumerate(ids_ordenados)}
    mapa_mats = {aid: f"LGPD-{idx + 1:03d}" for idx, aid in enumerate(ids_ordenados)}

    df_mask["Aluno"] = df_mask["aluno_id"].map(mapa_nomes)
    df_mask["Matrícula"] = df_mask["aluno_id"].map(mapa_mats)
    df_mask["E-mail"] = "oculto@lgpd.local"
    return df_mask


def carregar_desempenho(modelo_ia, anonimizar: bool = False) -> pd.DataFrame:
    with SessionLocal() as db:
        registros = db.query(Desempenho).join(Aluno).all()
        linhas = []
        for r in registros:
            disc = normalizar_disciplina(r.disciplina)
            if not disc:
                continue
            ativ = r.atividades if r.atividades is not None else 100.0
            alerta = avaliar_risco(r.nota, r.frequencia)
            prev = prever_risco_ml(modelo_ia, r.nota, r.frequencia, ativ)
            linhas.append({
                "id": r.id,
                "aluno_id": r.aluno.id,
                "Matrícula": r.aluno.matricula,
                "Aluno": r.aluno.nome,
                "Turma": r.aluno.turma,
                "E-mail": r.aluno.email_responsavel or "",
                "Disciplina": disc,
                "Período": r.periodo,
                "Nota": round(r.nota, 1),
                "Frequência (%)": round(r.frequencia, 1),
                "Atividades (%)": round(ativ, 1),
                "Status": alerta["nivel"],
                "Risco IA (%)": prev["probabilidade"],
                "Classificação": prev["faixa"],
                "Motivo": alerta["motivo"],
                "Recomendação": prev["recomendacao"],
            })
        df = pd.DataFrame(linhas)
        return anonimizar_dataframe(df) if anonimizar else df


def listar_alunos() -> list[dict]:
    with SessionLocal() as db:
        alunos = db.query(Aluno).order_by(Aluno.nome).all()
        return [
            {"id": a.id, "nome": a.nome, "matricula": a.matricula, "turma": a.turma}
            for a in alunos
        ]


def listar_lancamentos_simples() -> list[dict]:
    with SessionLocal() as db:
        registros = db.query(Desempenho).join(Aluno).order_by(Desempenho.id.desc()).all()
        return [
            {
                "id": r.id,
                "aluno": r.aluno.nome,
                "matricula": r.aluno.matricula,
                "disciplina": r.disciplina or "(vazio)",
                "periodo": r.periodo,
                "nota": float(r.nota),
                "frequencia": float(r.frequencia),
                "atividades": float(r.atividades if r.atividades is not None else 100.0),
            }
            for r in registros
        ]


def cadastrar_aluno(nome: str, matricula: str, turma: str, email: str) -> tuple[bool, str]:
    nome_l, mat_l, turma_l = " ".join(nome.split()), matricula.strip(), " ".join(turma.split())
    if not (nome_l and mat_l and turma_l):
        return False, "Preencha nome, matrícula e turma/curso."
    try:
        with SessionLocal() as db:
            db.add(Aluno(
                nome=nome_l,
                matricula=mat_l,
                turma=turma_l,
                email_responsavel=email.strip(),
            ))
            db.commit()
        return True, "Estudante cadastrado com sucesso."
    except IntegrityError:
        return False, "Já existe um estudante com essa matrícula."


def excluir_aluno(aluno_id: int) -> None:
    with SessionLocal() as db:
        alvo = db.query(Aluno).filter(Aluno.id == aluno_id).first()
        if alvo:
            db.delete(alvo)
            db.commit()


def registrar_desempenho(aluno_id: int, disciplina: str, periodo: str, nota: float, freq: float, ativ: float) -> tuple[bool, str]:
    valido, erro = validar_desempenho(disciplina, nota, freq, ativ)
    if not valido:
        return False, erro
    disc_padrao = normalizar_disciplina(disciplina)
    with SessionLocal() as db:
        existente = db.query(Desempenho).filter(
            Desempenho.aluno_id == aluno_id,
            Desempenho.disciplina == disc_padrao,
            Desempenho.periodo == periodo,
        ).first()
        if existente:
            existente.nota, existente.frequencia, existente.atividades = nota, freq, ativ
            db.commit()
            return True, f"Registro existente de {disc_padrao} ({periodo}) atualizado."
        db.add(Desempenho(
            aluno_id=aluno_id,
            disciplina=disc_padrao,
            periodo=periodo,
            nota=nota,
            frequencia=freq,
            atividades=ativ,
        ))
        db.commit()
    return True, "Desempenho registrado com sucesso."


def atualizar_desempenho(registro_id: int, disciplina: str, periodo: str, nota: float, freq: float, ativ: float) -> tuple[bool, str]:
    valido, erro = validar_desempenho(disciplina, nota, freq, ativ)
    if not valido:
        return False, erro
    with SessionLocal() as db:
        reg = db.query(Desempenho).filter(Desempenho.id == registro_id).first()
        if not reg:
            return False, "Lançamento não encontrado."
        reg.disciplina = normalizar_disciplina(disciplina)
        reg.periodo = periodo
        reg.nota = nota
        reg.frequencia = freq
        reg.atividades = ativ
        db.commit()
    return True, "Lançamento atualizado com sucesso."


def excluir_desempenho(registro_id: int) -> None:
    with SessionLocal() as db:
        reg = db.query(Desempenho).filter(Desempenho.id == registro_id).first()
        if reg:
            db.delete(reg)
            db.commit()


def higienizar_base() -> tuple[int, int]:
    """Remove registros com disciplina vazia e padroniza nomes duplicados (ex.: MATEMATICA -> Matemática)."""
    removidos, padronizados = 0, 0
    with SessionLocal() as db:
        for r in db.query(Desempenho).all():
            disc_limpa = normalizar_disciplina(r.disciplina)
            if not disc_limpa:
                db.delete(r)
                removidos += 1
            elif r.disciplina != disc_limpa:
                r.disciplina = disc_limpa
                padronizados += 1
        db.commit()
    return removidos, padronizados


def listar_intervencoes(aluno_id: int) -> list[dict]:
    with SessionLocal() as db:
        acoes = (
            db.query(Intervencao)
            .filter(Intervencao.aluno_id == aluno_id)
            .order_by(Intervencao.criado_em.desc())
            .all()
        )
        return [
            {
                "id": a.id,
                "Data": a.criado_em.strftime("%d/%m/%Y %H:%M"),
                "Tipo": a.tipo,
                "Responsável": a.responsavel_acao,
                "Status": a.status,
                "Observação": a.observacao or "—",
            }
            for a in acoes
        ]


def registrar_intervencao(aluno_id: int, tipo: str, responsavel: str, status: str, obs: str) -> None:
    with SessionLocal() as db:
        db.add(Intervencao(
            aluno_id=aluno_id,
            tipo=tipo,
            responsavel_acao=responsavel.strip() or "Coordenação Pedagógica",
            status=status,
            observacao=obs.strip(),
        ))
        db.commit()


def atualizar_intervencao(intervencao_id: int, novo_status: str, nova_obs: str) -> None:
    with SessionLocal() as db:
        alvo = db.query(Intervencao).filter(Intervencao.id == intervencao_id).first()
        if alvo:
            alvo.status = novo_status
            if nova_obs.strip():
                alvo.observacao = nova_obs.strip()
            db.commit()


def importar_planilha(df_up: pd.DataFrame, mapa: dict) -> tuple[int, int, int]:
    novos, atualizados, ignorados = 0, 0, 0
    with SessionLocal() as db:
        for _, row in df_up.iterrows():
            nome = " ".join(str(row[mapa["nome"]]).strip().split())
            mat = str(row[mapa["matricula"]]).strip()
            turma = " ".join(str(row[mapa["turma"]]).strip().split())
            disc = normalizar_disciplina(row[mapa["disciplina"]])
            per = str(row[mapa["periodo"]]).strip()
            nota = limpar_numero(row[mapa["nota"]], -1.0)
            freq = limpar_numero(row[mapa["frequencia"]], -1.0)
            ativ = 100.0 if not mapa["atividades"] else limpar_numero(row[mapa["atividades"]], 100.0)

            valido, _ = validar_desempenho(disc, nota, freq, ativ)
            if not (nome and mat and turma and per and valido):
                ignorados += 1
                continue

            email_col = mapa["email"]
            email_val = "" if not email_col or pd.isna(row[email_col]) else str(row[email_col]).strip()

            aluno = db.query(Aluno).filter(Aluno.matricula == mat).first()
            if not aluno:
                aluno = Aluno(nome=nome, matricula=mat, turma=turma, email_responsavel=email_val)
                db.add(aluno)
                db.flush()

            existente = db.query(Desempenho).filter(
                Desempenho.aluno_id == aluno.id,
                Desempenho.disciplina == disc,
                Desempenho.periodo == per,
            ).first()

            if existente:
                existente.nota, existente.frequencia, existente.atividades = nota, freq, ativ
                atualizados += 1
            else:
                db.add(Desempenho(
                    aluno_id=aluno.id, disciplina=disc, periodo=per,
                    nota=nota, frequencia=freq, atividades=ativ,
                ))
                novos += 1
        db.commit()
    return novos, atualizados, ignorados


def popular_dados_demo() -> int:
    amostra = [
        ("Ana Beatriz Silva", "2026101", "ADS - 2º Período", "ana@instituicao.edu", "Algoritmos", "1º Semestre", 8.8, 96, 95),
        ("Ana Beatriz Silva", "2026101", "ADS - 2º Período", "ana@instituicao.edu", "Banco de Dados", "1º Semestre", 8.2, 92, 90),
        ("Bruno Henrique Costa", "2026102", "ADS - 2º Período", "bruno@instituicao.edu", "Algoritmos", "1º Semestre", 6.4, 80, 35),
        ("Bruno Henrique Costa", "2026102", "ADS - 2º Período", "bruno@instituicao.edu", "Banco de Dados", "1º Semestre", 5.8, 76, 40),
        ("Carla Mendes Rocha", "2026103", "ADS - 2º Período", "carla@instituicao.edu", "Algoritmos", "1º Semestre", 3.9, 64, 20),
        ("Carla Mendes Rocha", "2026103", "ADS - 2º Período", "carla@instituicao.edu", "Cálculo I", "1º Semestre", 4.2, 68, 25),
        ("Diego Lima Souza", "2026104", "3º Ano A", "resp.diego@email.com", "Matemática", "1º Bimestre", 7.6, 90, 85),
        ("Diego Lima Souza", "2026104", "3º Ano A", "resp.diego@email.com", "Matemática", "2º Bimestre", 5.5, 78, 42),
        ("Fernanda Alves", "2026105", "3º Ano A", "resp.fernanda@email.com", "Física", "1º Bimestre", 4.6, 71, 30),
        ("Gabriel Oliveira", "2026106", "3º Ano A", "resp.gabriel@email.com", "Física", "1º Bimestre", 9.2, 98, 100),
    ]
    inseridos = 0
    with SessionLocal() as db:
        for nome, mat, turma, email, disc, per, nota, freq, ativ in amostra:
            aluno = db.query(Aluno).filter(Aluno.matricula == mat).first()
            if not aluno:
                aluno = Aluno(nome=nome, matricula=mat, turma=turma, email_responsavel=email)
                db.add(aluno)
                db.flush()
            disc_p = normalizar_disciplina(disc)
            existe = db.query(Desempenho).filter(
                Desempenho.aluno_id == aluno.id,
                Desempenho.disciplina == disc_p,
                Desempenho.periodo == per,
            ).first()
            if not existe:
                db.add(Desempenho(
                    aluno_id=aluno.id, disciplina=disc_p, periodo=per,
                    nota=nota, frequencia=freq, atividades=ativ,
                ))
                inseridos += 1
        db.commit()
    return inseridos
