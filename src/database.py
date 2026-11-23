from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = "sqlite:///sentinela.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Aluno(Base):
    __tablename__ = "alunos"

    id = Column(Integer, primary_key=True, index=True)
    matricula = Column(String(30), unique=True, nullable=False)
    nome = Column(String(120), nullable=False)
    curso = Column(String(100), nullable=False)
    semestre = Column(Integer, nullable=False)
    email_aluno = Column(String(120), nullable=False)

    # Indicadores acadêmicos e comportamentais
    media_notas = Column(Float, nullable=False)
    frequencia_pct = Column(Float, nullable=False)
    acessos_ava_semana = Column(Integer, nullable=False)
    reprovacoes = Column(Integer, default=0)
    dias_atraso_mensalidade = Column(Integer, default=0)
    satisfacao_curso = Column(Integer, default=4)  # Escala 1 a 5

    alertas = relationship("LogAlerta", back_populates="aluno", cascade="all, delete-orphan")


class LogAlerta(Base):
    __tablename__ = "logs_alertas"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"), nullable=False)
    criado_em = Column(DateTime, default=datetime.now)
    diagnostico_ml = Column(String(50), nullable=False)
    probabilidade = Column(Float, nullable=False)
    prioridade = Column(String(20), nullable=False)
    msg_coordenacao = Column(Text, nullable=False)
    msg_aluno = Column(Text, nullable=False)
    status_envio = Column(String(40), default="Disparado (Simulação)")

    aluno = relationship("Aluno", back_populates="alertas")


def init_db():
    Base.metadata.create_all(bind=engine)


def popular_base_inicial():
    with SessionLocal() as db:
        if db.query(Aluno).count() > 0:
            return
        amostra = [
            Aluno(
                matricula="2026001", nome="Mariana Costa", curso="Análise e Desenv. de Sistemas",
                semestre=2, email_aluno="mariana.costa@faculdade.edu",
                media_notas=8.7, frequencia_pct=94.0, acessos_ava_semana=12,
                reprovacoes=0, dias_atraso_mensalidade=0, satisfacao_curso=5
            ),
            Aluno(
                matricula="2026002", nome="Lucas Ferreira", curso="Engenharia de Software",
                semestre=3, email_aluno="lucas.ferreira@faculdade.edu",
                media_notas=4.1, frequencia_pct=58.0, acessos_ava_semana=1,
                reprovacoes=3, dias_atraso_mensalidade=45, satisfacao_curso=2
            ),
            Aluno(
                matricula="2026003", nome="Beatriz Almeida", curso="Administração",
                semestre=4, email_aluno="beatriz.almeida@faculdade.edu",
                media_notas=7.4, frequencia_pct=82.0, acessos_ava_semana=6,
                reprovacoes=0, dias_atraso_mensalidade=60, satisfacao_curso=4
            ),
            Aluno(
                matricula="2026004", nome="Rafael Mendes", curso="Sistemas de Informação",
                semestre=1, email_aluno="rafael.mendes@faculdade.edu",
                media_notas=7.8, frequencia_pct=88.0, acessos_ava_semana=8,
                reprovacoes=0, dias_atraso_mensalidade=0, satisfacao_curso=1
            ),
            Aluno(
                matricula="2026005", nome="Camila Rocha", curso="Análise e Desenv. de Sistemas",
                semestre=5, email_aluno="camila.rocha@faculdade.edu",
                media_notas=5.3, frequencia_pct=68.0, acessos_ava_semana=2,
                reprovacoes=2, dias_atraso_mensalidade=15, satisfacao_curso=2
            ),
        ]
        db.add_all(amostra)
        db.commit()
