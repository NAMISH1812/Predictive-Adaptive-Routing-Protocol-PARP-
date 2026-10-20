import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

import os
import joblib


INPUT_FILE = "telemetry/data/ml_dataset.csv"
MODEL_FILE = "prediction/congestion_model.pkl"


def train_model():

    df = pd.read_csv(INPUT_FILE)

    features = [
        "utilization_percent",
        "rtt_ms",
        "jitter_ms",
        "packet_loss_percent"
    ]

    target = "congestion_score"

    X = df[features]
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("regressor", LinearRegression())
    ])

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    mae = mean_absolute_error(
        y_test,
        predictions
    )

    r2 = r2_score(
        y_test,
        predictions
    )

    os.makedirs(
        "prediction",
        exist_ok=True
    )

    joblib.dump(
        model,
        MODEL_FILE
    )

    print()
    print("======================================")
    print("PARP Linear Regression")
    print("======================================")
    print(f"Training samples : {len(X_train)}")
    print(f"Testing samples  : {len(X_test)}")
    print()
    print("Features:")
    for feature in features:
        print(f"- {feature}")
    print()
    print(f"MAE : {mae:.6f}")
    print(f"R²  : {r2:.6f}")
    print()
    print(f"Model saved: {MODEL_FILE}")
    print("======================================")

    print()
    print("Sample predictions:")
    print()

    results = pd.DataFrame({
        "actual": y_test.values,
        "predicted": predictions
    })

    print(
        results.head(10).to_string(
            index=False
        )
    )


if __name__ == "__main__":
    train_model()
