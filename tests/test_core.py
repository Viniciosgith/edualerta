from alertas import avaliar_risco
from modelo_ml import treinar_modelo, prever_risco_ml
from services import normalizar_disciplina, validar_desempenho


def test_alerta_critico_por_nota_ou_frequencia_ldb():
    assert avaliar_risco(4.5, 90.0)["nivel"] == "CRÍTICO"
    assert avaliar_risco(8.5, 70.0)["nivel"] == "CRÍTICO"


def test_alerta_atencao_e_normal():
    assert avaliar_risco(6.2, 88.0)["nivel"] == "ATENÇÃO"
    assert avaliar_risco(8.0, 92.0)["nivel"] == "NORMAL"


def test_normalizacao_disciplinas():
    assert normalizar_disciplina("  MATEMATICA ") == "Matemática"
    assert normalizar_disciplina("calculo i") == "Cálculo I"
    assert normalizar_disciplina("   ") == ""


def test_validacao_limites_desempenho():
    assert validar_desempenho("Física", 7.5, 85.0, 90.0)[0] is True
    assert validar_desempenho("", 7.5, 85.0, 90.0)[0] is False
    assert validar_desempenho("Física", 11.0, 85.0, 90.0)[0] is False
    assert validar_desempenho("Física", 7.5, -5.0, 90.0)[0] is False


def test_modelo_ml_previsao_e_metricas():
    modelo, metricas, _, _ = treinar_modelo()
    assert metricas["acuracia"] >= 80.0
    alto = prever_risco_ml(modelo, 3.5, 60.0, 15.0)
    baixo = prever_risco_ml(modelo, 9.2, 96.0, 98.0)
    assert alto["faixa"] == "ALTO RISCO"
    assert baixo["faixa"] == "BAIXO RISCO"
