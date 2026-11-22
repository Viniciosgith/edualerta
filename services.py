import pandas as pd
from sqlalchemy.exc import IntegrityError
from database import SessionLocal, Aluno, Desempenho, Intervencao
from alertas import avaliar_risco
from modelo_ml import prever_risco_ml


def limpar_numero(valor, padrao: float = 0.0) -> float:
    if pd.isna(valor):
        return padrao
    try:
        return float(str(valor).replace(",", ".").replace("%", "").strip())
    except ValueError:
        return padrao


def carregar_desempenho(modelo_ia) -> pd.DataFrame:
    with SessionLocal() as db:
        registros = db.query(Desempenho).join(Aluno).all()
        linhas = []
        for r in registros:
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
                "Disciplina": r.disciplina,
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
        return pd.DataFrame(linhas)


def listar_alunos() -> list[dict]:
    with SessionLocal() as db:
        alunos = db.query(Aluno).order_by(Aluno.nome).all()
        return [
            {"id": a.id, "nome": a.nome, "matricula": a.matricula, "turma": a.turma}
            for a in alunos
        ]


def cadastrar_aluno(nome: str, matricula: str, turma: str, email: str) -> tuple[bool, str]:
    try:
        with SessionLocal() as db:
            db.add(Aluno(
                nome=nome.strip(),
                matricula=matricula.strip(),
                turma=turma.strip(),
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


def registrar_desempenho(aluno_id: int, disciplina: str, periodo: str, nota: float, freq: float, ativ: float) -> None:
    with SessionLocal() as db:
        db.add(Desempenho(
            aluno_id=aluno_id,
            disciplina=disciplina.strip(),
            periodo=periodo,
            nota=nota,
            frequencia=freq,
            atividades=ativ,
        ))
        db.commit()


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
            responsavel_acao=responsavel.strip(),
            status=status,
            observacao=obs.strip(),
        ))
        db.commit()


def importar_planilha(df_up: pd.DataFrame, mapa: dict) -> tuple[int, int]:
    novos, atualizados = 0, 0
    with SessionLocal() as db:
        for _, row in df_up.iterrows():
            mat = str(row[mapa["matricula"]]).strip()
            email_col = mapa["email"]
            email_val = "" if not email_col or pd.isna(row[email_col]) else str(row[email_col]).strip()

            aluno = db.query(Aluno).filter(Aluno.matricula == mat).first()
            if not aluno:
                aluno = Aluno(
                    nome=str(row[mapa["nome"]]).strip(),
                    matricula=mat,
                    turma=str(row[mapa["turma"]]).strip(),
                    email_responsavel=email_val,
                )
                db.add(aluno)
                db.flush()

            disc = str(row[mapa["disciplina"]]).strip()
            per = str(row[mapa["periodo"]]).strip()
            nota = limpar_numero(row[mapa["nota"]])
            freq = limpar_numero(row[mapa["frequencia"]])
            ativ = 100.0 if not mapa["atividades"] else limpar_numero(row[mapa["atividades"]], 100.0)

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
    return novos, atualizados


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
            existe = db.query(Desempenho).filter(
                Desempenho.aluno_id == aluno.id,
                Desempenho.disciplina == disc,
                Desempenho.periodo == per,
            ).first()
            if not existe:
                db.add(Desempenho(
                    aluno_id=aluno.id, disciplina=disc, periodo=per,
                    nota=nota, frequencia=freq, atividades=ativ,
                ))
                inseridos += 1
        db.commit()
    return inseridos
