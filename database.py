import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///escola.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Aluno(Base):
    __tablename__ = "alunos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    matricula = Column(String(30), unique=True, nullable=False)
    turma = Column(String(50), nullable=False)
    email_responsavel = Column(String(120), nullable=True)
    registros = relationship("Desempenho", back_populates="aluno", cascade="all, delete")

class Desempenho(Base):
    __tablename__ = "desempenho"
    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"), nullable=False)
    disciplina = Column(String(80), nullable=False)
    nota = Column(Float, nullable=False)
    frequencia = Column(Float, nullable=False)  # Percentual de 0 a 100
    periodo = Column(String(30), nullable=False)  # Ex.: 1º Bimestre
    criado_em = Column(DateTime, default=datetime.utcnow)
    aluno = relationship("Aluno", back_populates="registros")

def inicializar_banco():
    Base.metadata.create_all(bind=engine)