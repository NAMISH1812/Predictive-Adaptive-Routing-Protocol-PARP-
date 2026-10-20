import os

import joblib
import pandas as pd

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ============================================================
# CONFIGURATION
# ============================================================

DATA_FILE = (
    "telemetry/data/ml_dataset_phase2.csv"
)

MODEL_FILE = (
    "prediction/future_utilization_model.pkl"
)

FEATURES = [
    "utilization_percent",
    "utilization_lag1",
    "utilization_lag2",
    "utilization_change",
    "rtt_ms",
    "jitter_ms",
    "packet_loss_percent",
]

TARGET = "future_utilization"


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 50)
print("PARP Phase 2 Linear Regression")
print("=" * 50)

df = pd.read_csv(DATA_FILE)

print(f"Dataset rows : {len(df)}")
print(f"Features     : {len(FEATURES)}")


# ============================================================
# PREPARE X AND Y
# ============================================================

X = df[FEATURES]
y = df[TARGET]


# ============================================================
# CHRONOLOGICAL TRAIN/TEST SPLIT
# ============================================================

split_index = int(len(df) * 0.80)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]


print()
print("Train/Test Split")
print("-" * 30)
print(f"Training samples : {len(X_train)}")
print(f"Testing samples  : {len(X_test)}")


# ============================================================
# MODEL PIPELINE
# ============================================================

model = Pipeline([
    (
        "scaler",
        StandardScaler()
    ),
    (
        "regressor",
        LinearRegression()
    )
])


# ============================================================
# TRAIN
# ============================================================

print()
print("Training Linear Regression...")

model.fit(
    X_train,
    y_train
)


# ============================================================
# PREDICTION
# ============================================================

y_pred = model.predict(
    X_test
)

# Utilization cannot be below 0
# or above 100 percent.

y_pred = y_pred.clip(
    0,
    100
)


# ============================================================
# EVALUATION
# ============================================================

mae = mean_absolute_error(
    y_test,
    y_pred
)

r2 = r2_score(
    y_test,
    y_pred
)


print()
print("=" * 50)
print("MODEL RESULTS")
print("=" * 50)

print(
    f"MAE : {mae:.4f}"
)

print(
    f"R²  : {r2:.4f}"
)


# ============================================================
# SAMPLE PREDICTIONS
# ============================================================

results = pd.DataFrame({
    "actual": y_test.values,
    "predicted": y_pred
})

print()
print("Sample Predictions")
print("-" * 50)
print(
    results.head(15).to_string(
        index=False
    )
)


# ============================================================
# SAVE MODEL
# ============================================================

os.makedirs(
    "prediction",
    exist_ok=True
)

joblib.dump(
    model,
    MODEL_FILE
)

print()
print(
    f"Model saved to: {MODEL_FILE}"
)

print("=" * 50)