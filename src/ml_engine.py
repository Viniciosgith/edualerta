import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = [
    "media_notas",
    "frequencia_pct",
    "acessos_ava_semana",
    "reprovacoes",
    "dias_atraso_mensalidade",
    "satisfacao_curso",
]

CLASSES = [
    "Permanência",
    "Risco de Trancamento",
    "Risco de Mudança de Curso",
    "Risco de Evasão",
]


def _gerar_dataset_sintetico(n_amostras: int = 1200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dados = []

    for _ in range(n_amostras):
        perfil = rng.choice(CLASSES, p=[0.45, 0.20, 0.15, 0.20])

        if perfil == "Permanência":
            nota = np.clip(rng.normal(8.0, 1.0), 5.5, 10.0)
            freq = np.clip(rng.normal(90, 6), 75, 100)
            ava = int(np.clip(rng.normal(10, 3), 4, 20))
            reprov = int(rng.choice([0, 1], p=[0.85, 0.15]))
            atraso = int(rng.choice([0, 5, 10], p=[0.85, 0.10, 0.05]))
            sat = int(rng.choice([4, 5], p=[0.4, 0.6]))

        elif perfil == "Risco de Trancamento":
            # Aluno que acompanha o curso, mas enfrenta barreira financeira ou de tempo
            nota = np.clip(rng.normal(7.0, 1.1), 4.5, 9.5)
            freq = np.clip(rng.normal(76, 8), 60, 92)
            ava = int(np.clip(rng.normal(5, 2), 1, 10))
            reprov = int(rng.choice([0, 1, 2], p=[0.5, 0.35, 0.15]))
            atraso = int(np.clip(rng.normal(50, 18), 20, 90))
            sat = int(rng.choice([3, 4, 5], p=[0.3, 0.4, 0.3]))

        elif perfil == "Risco de Mudança de Curso":
            # Desempenho razoável/bom, mas baixa identificação com o curso
            nota = np.clip(rng.normal(7.2, 1.2), 5.0, 9.8)
            freq = np.clip(rng.normal(82, 8), 65, 98)
            ava = int(np.clip(rng.normal(7, 2), 3, 14))
            reprov = int(rng.choice([0, 1], p=[0.75, 0.25]))
            atraso = int(rng.choice([0, 5, 15], p=[0.8, 0.15, 0.05]))
            sat = int(rng.choice([1, 2], p=[0.6, 0.4]))

        else:  # Risco de Evasão
            nota = np.clip(rng.normal(4.3, 1.3), 0.5, 6.8)
            freq = np.clip(rng.normal(58, 12), 20, 78)
            ava = int(np.clip(rng.normal(2, 1.5), 0, 6))
            reprov = int(rng.choice([1, 2, 3, 4], p=[0.15, 0.35, 0.30, 0.20]))
            atraso = int(np.clip(rng.normal(35, 25), 0, 90))
            sat = int(rng.choice([1, 2, 3], p=[0.5, 0.35, 0.15]))

        dados.append({
            "media_notas": round(float(nota), 1),
            "frequencia_pct": round(float(freq), 1),
            "acessos_ava_semana": ava,
            "reprovacoes": reprov,
            "dias_atraso_mensalidade": atraso,
            "satisfacao_curso": sat,
            "alvo": perfil,
        })

    return pd.DataFrame(dados)


def treinar_pipeline():
    df = _gerar_dataset_sintetico()
    X = df[FEATURES]
    y = df["alvo"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(
            n_estimators=180,
            max_depth=10,
            class_weight="balanced",
            random_state=42,
        )),
    ])
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    metricas = {
        "acuracia": round(accuracy_score(y_test, y_pred) * 100, 1),
        "f1_macro": round(f1_score(y_test, y_pred, average="macro") * 100, 1),
    }
    return pipeline, metricas


def diagnosticar_aluno(pipeline, dados_aluno: dict) -> dict:
    df_in = pd.DataFrame([{col: dados_aluno[col] for col in FEATURES}])
    probs = pipeline.predict_proba(df_in)[0]
    classes = list(pipeline.named_steps["clf"].classes_)

    idx_max = int(np.argmax(probs))
    diagnostico = classes[idx_max]
    confianca = round(float(probs[idx_max]) * 100, 1)

    # Explicabilidade dos principais gatilhos individuais
    fatores = []
    if dados_aluno["media_notas"] < 6.0:
        fatores.append(f"Média baixa ({dados_aluno['media_notas']:.1f})")
    if dados_aluno["frequencia_pct"] < 75.0:
        fatores.append(f"Frequência abaixo do limite ({dados_aluno['frequencia_pct']:.0f}%)")
    if dados_aluno["acessos_ava_semana"] <= 2:
        fatores.append(f"Baixo engajamento no AVA ({dados_aluno['acessos_ava_semana']}x/sem)")
    if dados_aluno["reprovacoes"] >= 2:
        fatores.append(f"Acúmulo de reprovações ({dados_aluno['reprovacoes']})")
    if dados_aluno["dias_atraso_mensalidade"] >= 20:
        fatores.append(f"Inadimplência ({dados_aluno['dias_atraso_mensalidade']} dias)")
    if dados_aluno["satisfacao_curso"] <= 2:
        fatores.append(f"Baixa satisfação com o curso ({dados_aluno['satisfacao_curso']}/5)")

    if not fatores:
        fatores.append("Indicadores dentro da faixa saudável")

    return {
        "diagnostico": diagnostico,
        "probabilidade": confianca,
        "fatores": fatores,
        "distribuicao": {c: round(float(p) * 100, 1) for c, p in zip(classes, probs)},
    }
