
"""
PARP Research Paper Graph Generator
-----------------------------------
Generates four publication-quality figures:
1. Link utilization observations
2. RTT observations
3. Actual vs. predicted future utilization
4. Average utilization by link

Run from the PARP project using the activated virtual environment.
"""

from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------
# 1. PATHS AND CONFIGURATION
# ---------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

TELEMETRY_FILE = (
    PROJECT_DIR / "telemetry" / "data" / "telemetry_processed.csv"
)

ML_DATASET_FILE = (
    PROJECT_DIR / "telemetry" / "data" / "ml_dataset_phase2.csv"
)

OUTPUT_DIR = PROJECT_DIR / "paper_figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LINKS = ["r1-r2", "r2-r4", "r1-r3", "r3-r4"]

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

plt.rcParams.update({
    "figure.figsize": (10, 5.5),
    "figure.dpi": 120,
    "savefig.dpi": 300,
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "legend.fontsize": 9,
    "lines.linewidth": 1.5,
})


def check_file(path):
    """Stop with a useful message if a required file is missing."""
    if not path.exists():
        print(f"\nERROR: Required file not found:\n{path}")
        sys.exit(1)


def save_figure(filename):
    """Save the current figure as a high-resolution PNG."""
    output_path = OUTPUT_DIR / filename

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output_path}")


def load_telemetry():
    """Load and validate the raw telemetry CSV."""
    check_file(TELEMETRY_FILE)

    data = pd.read_csv(TELEMETRY_FILE)

    required = [
        "timestamp",
        "link",
        "utilization_percent",
        "rtt_ms",
    ]

    missing = [col for col in required if col not in data.columns]

    if missing:
        print(f"ERROR: Missing telemetry columns: {missing}")
        sys.exit(1)

    data["timestamp"] = pd.to_datetime(
        data["timestamp"], errors="coerce"
    )

    data["utilization_percent"] = pd.to_numeric(
        data["utilization_percent"], errors="coerce"
    )

    data["rtt_ms"] = pd.to_numeric(
        data["rtt_ms"], errors="coerce"
    )

    data = data.dropna(subset=["timestamp", "link"])
    data["link"] = data["link"].astype(str)

    data["utilization_percent"] = (
        data["utilization_percent"].clip(0, 100)
    )

    data = data.sort_values("timestamp").reset_index(drop=True)

    if data.empty:
        print("ERROR: The telemetry dataset is empty.")
        sys.exit(1)

    return data


# ---------------------------------------------------------
# 2. FIGURE 1: LINK UTILIZATION OBSERVATIONS
# ---------------------------------------------------------

def plot_link_utilization(data):
    plt.figure()

    plotted = False

    for link in LINKS:
        subset = (
            data[data["link"] == link]
            .sort_values("timestamp")
            .dropna(subset=["utilization_percent"])
            .reset_index(drop=True)
        )

        if subset.empty:
            continue

        # Use observation index instead of calendar time.
        # This prevents lines from connecting measurements
        # across long periods when no data was collected.
        x = np.arange(1, len(subset) + 1)

        plt.plot(
            x,
            subset["utilization_percent"],
            marker="o",
            markersize=3,
            linestyle="-",
            label=link,
        )

        plotted = True

    if not plotted:
        plt.close()
        print("WARNING: No utilization observations available.")
        return

    plt.title("Link Utilization Observations")
    plt.xlabel("Telemetry observation index (per link)")
    plt.ylabel("Utilization (%)")
    plt.ylim(-2, 105)
    plt.grid(True, alpha=0.3)
    plt.legend(title="Link")

    save_figure("fig1_link_utilization.png")


# ---------------------------------------------------------
# 3. FIGURE 2: ROUND-TRIP TIME
# ---------------------------------------------------------

def plot_rtt(data):
    plt.figure()

    plotted = False

    for link in LINKS:
        subset = (
            data[data["link"] == link]
            .sort_values("timestamp")
            .dropna(subset=["rtt_ms"])
            .reset_index(drop=True)
        )

        if subset.empty:
            continue

        # Keep the actual RTT values. Do not replace missing
        # measurements with zero or fabricate observations.
        subset = subset[subset["rtt_ms"] >= 0]

        if subset.empty:
            continue

        x = np.arange(1, len(subset) + 1)

        plt.plot(
            x,
            subset["rtt_ms"],
            marker="o",
            markersize=3,
            linestyle="-",
            label=link,
        )

        plotted = True

    if not plotted:
        plt.close()
        print("WARNING: No valid RTT observations available.")
        return

    plt.title("Round-Trip Time Observations")
    plt.xlabel("Telemetry observation index (per link)")
    plt.ylabel("RTT (ms)")
    plt.grid(True, alpha=0.3)
    plt.legend(title="Link")

    save_figure("fig2_rtt.png")


# ---------------------------------------------------------
# 4. FIGURE 3: ACTUAL VS. PREDICTED FUTURE UTILIZATION
# ---------------------------------------------------------

def plot_predictions():
    check_file(ML_DATASET_FILE)

    data = pd.read_csv(ML_DATASET_FILE)

    required = ["timestamp", *FEATURES, TARGET]
    missing = [col for col in required if col not in data.columns]

    if missing:
        print(f"ERROR: Missing ML dataset columns: {missing}")
        sys.exit(1)

    data["timestamp"] = pd.to_datetime(
        data["timestamp"], errors="coerce"
    )

    for col in FEATURES + [TARGET]:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = (
        data.dropna(subset=["timestamp", *FEATURES, TARGET])
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    if len(data) < 10:
        print("ERROR: Not enough valid samples for model evaluation.")
        sys.exit(1)

    # Chronological split: earlier observations for training,
    # later observations for testing. No random shuffle.
    split_index = int(len(data) * 0.80)

    train = data.iloc[:split_index]
    test = data.iloc[split_index:]

    if len(test) < 2:
        print("ERROR: The test set contains too few observations.")
        sys.exit(1)

    X_train = train[FEATURES]
    y_train = train[TARGET]

    X_test = test[FEATURES]
    y_test = test[TARGET].clip(0, 100)

    # Reproduce the documented StandardScaler + LinearRegression
    # pipeline using this dataset and the chronological split.
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("regressor", LinearRegression()),
    ])

    model.fit(X_train, y_train)

    predictions = np.clip(model.predict(X_test), 0, 100)

    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    print("\n" + "=" * 55)
    print("PARP FUTURE UTILIZATION MODEL EVALUATION")
    print("=" * 55)
    print(f"Total valid samples : {len(data)}")
    print(f"Training samples    : {len(train)}")
    print(f"Testing samples     : {len(test)}")
    print(f"MAE                 : {mae:.4f}")
    print(f"R-squared           : {r2:.4f}")
    print("=" * 55)

    # Plot by chronological test-sample order, not by dates.
    # This avoids misleading calendar gaps and keeps every
    # actual value aligned with its corresponding prediction.
    x = np.arange(1, len(test) + 1)

    plt.figure()

    plt.plot(
        x,
        y_test.to_numpy(),
        marker="o",
        markersize=3,
        label="Actual",
    )

    plt.plot(
        x,
        predictions,
        marker="x",
        markersize=4,
        label="Predicted",
    )

    plt.title(
        "Actual vs. Predicted Future Utilization\n"
        f"(MAE = {mae:.2f}, R² = {r2:.3f})"
    )

    plt.xlabel("Chronological test sample")
    plt.ylabel("Future utilization (%)")
    plt.ylim(-2, 105)
    plt.grid(True, alpha=0.3)
    plt.legend()

    save_figure("fig3_actual_vs_predicted.png")

    # Save the metrics separately so they can be checked
    # before being entered into the research paper.
    metrics = pd.DataFrame({
        "metric": ["MAE", "R_squared"],
        "value": [mae, r2],
    })

    metrics.to_csv(
        OUTPUT_DIR / "model_evaluation_metrics.csv",
        index=False,
    )

    print(f"Saved: {OUTPUT_DIR / 'model_evaluation_metrics.csv'}")


# ---------------------------------------------------------
# 5. FIGURE 4: AVERAGE UTILIZATION BY LINK
# ---------------------------------------------------------

def plot_average_utilization(data):
    averages = (
        data.groupby("link")["utilization_percent"]
        .mean()
        .reindex(LINKS)
    )

    # Keep genuinely missing links missing rather than
    # reporting a fabricated average of zero.
    available = averages.dropna()

    if available.empty:
        print("WARNING: No average utilization values available.")
        return

    plt.figure()

    bars = plt.bar(
        available.index,
        available.values,
        width=0.7,
    )

    plt.title("Average Link Utilization")
    plt.xlabel("Link")
    plt.ylabel("Average utilization (%)")
    plt.ylim(0, max(10, float(available.max()) * 1.2))
    plt.grid(axis="y", alpha=0.3)

    for bar, value in zip(bars, available.values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.4,
            f"{value:.2f}%",
            ha="center",
            va="bottom",
        )

    save_figure("fig4_average_utilization.png")

    print("\nAverage utilization by link:")
    print(averages.to_string())


# ---------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------

def main():
    print("=" * 55)
    print("PARP RESEARCH PAPER GRAPH GENERATOR")
    print("=" * 55)

    print(f"Project directory: {PROJECT_DIR}")
    print(f"Output directory : {OUTPUT_DIR}")

    telemetry = load_telemetry()

    print(f"\nRaw telemetry rows: {len(telemetry)}")
    print("\nRows per link:")
    print(telemetry.groupby("link").size().to_string())

    plot_link_utilization(telemetry)
    plot_rtt(telemetry)
    plot_predictions()
    plot_average_utilization(telemetry)

    print("\n" + "=" * 55)
    print("GRAPH GENERATION FINISHED")
    print("=" * 55)
    print(f"Check the figures here:\n{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
