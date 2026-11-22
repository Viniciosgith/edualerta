import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

COLUNAS = ["nota", "frequencia", "atividades"]

def treinar_modelo():
    """Treina modelo Random Forest e retorna modelo, acurácia e peso das variáveis."""
    rng = np.random.default_rng(42)
    qtd = 500

    notas = rng.uniform(0, 10, qtd)
    frequencias = rng.uniform(40, 100, qtd)
    atividades = rng.uniform(0, 100, qtd)

    indice = (notas * 5.0) + (frequencias * 0.30) + (atividades * 0.20) + rng.normal(0, 4.0, qtd)
    em_risco = ((indice < 62) | (notas < 5.0) | (frequencias < 75.0)).astype(int)

    X = pd.DataFrame({"nota": notas, "frequencia": frequencias, "atividades": atividades})
    y = em_risco

    X_treino, X_teste, y_treino, y_teste = train_test_split(X, y, test_size=0.2, random_state=42)

    modelo = RandomForestClassifier(n_estimators=120, random_state=42)
    modelo.fit(X_treino, y_treino)

    acuracia = round(accuracy_score(y_teste, modelo.predict(X_teste)) * 100, 1)
    importancias = pd.DataFrame({
        "Fator": ["Nota", "Frequência (%)", "Atividades Entregues (%)"],
        "Peso (%)": [round(v * 100, 1) for v in modelo.feature_importances_]
    }).sort_values("Peso (%)", ascending=True)

    return modelo, acuracia, importancias

def prever_risco_ml(modelo, nota: float, frequencia: float, atividades: float) -> dict:
    """Calcula probabilidade de risco (0% a 100%) e sugere intervenção pedagógica."""
    entrada = pd.DataFrame([[nota, frequencia, atividades]], columns=COLUNAS)
    prob = round(float(modelo.predict_proba(entrada)[0][1] * 100), 1)

    if prob >= 70:
        faixa = "ALTO RISCO"
    elif prob >= 35:
        faixa = "RISCO MODERADO"
    else:
        faixa = "BAIXO RISCO"

    acoes = []
    if frequencia < 75:
        acoes.append("Acionar coordenação/responsável por risco de reprovação por falta")
    if nota < 6.0:
        acoes.append("Encaminhar para monitoria ou plantão de dúvidas na disciplina")
    if atividades < 60:
        acoes.append("Revisar engajamento e entregas atrasadas no AVA/portal")
    if not acoes:
        acoes.append("Manter acompanhamento regular")

    return {
        "probabilidade": prob,
        "faixa": faixa,
        "recomendacao": " • ".join(acoes)
    }
