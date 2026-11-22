import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///escola.db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Aluno(Base):
    __tablename__ = "alunos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    matricula = Column(String(30), unique=True, nullable=False)
    turma = Column(String(60), nullable=False)
    email_responsavel = Column(String(120), nullable=True)
    registros = relationship("Desempenho", back_populates="aluno", cascade="all, delete-orphan")
    intervencoes = relationship("Intervencao", back_populates="aluno", cascade="all, delete-orphan")

class Desempenho(Base):
    __tablename__ = "desempenho"
    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"), nullable=False)
    disciplina = Column(String(80), nullable=False)
    nota = Column(Float, nullable=False)
    frequencia = Column(Float, nullable=False)
    atividades = Column(Float, nullable=False, default=100.0)
    periodo = Column(String(30), nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    aluno = relationship("Aluno", back_populates="registros")

class Intervencao(Base):
    __tablename__ = "intervencoes"
    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"), nullable=False)
    tipo = Column(String(80), nullable=False)
    responsavel_acao = Column(String(100), nullable=False)
    status = Column(String(30), nullable=False, default="Pendente")
    observacao = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    aluno = relationship("Aluno", back_populates="intervencoes")

def inicializar_banco():
    Base.metadata.create_all(bind=engine)
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE desempenho ADD COLUMN atividades FLOAT NOT NULL DEFAULT 100.0"))
    except Exception:
        pass
