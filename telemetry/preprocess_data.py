import os

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = (
    "telemetry/data/telemetry_processed.csv"
)

OUTPUT_FILE = (
    "telemetry/data/ml_dataset_phase2.csv"
)


# ============================================================
# MAIN PREPROCESSING
# ============================================================

def preprocess():

    print("=" * 38)
    print("PARP Phase 2 Preprocessing")
    print("=" * 38)

    # --------------------------------------------------------
    # Load telemetry
    # --------------------------------------------------------

    df = pd.read_csv(
        INPUT_FILE
    )

    print(
        f"Original rows : {len(df)}"
    )

    print(
        f"Original columns : {len(df.columns)}"
    )

    # --------------------------------------------------------
    # Convert timestamp
    # --------------------------------------------------------

    df["timestamp"] = pd.to_datetime(
        df["timestamp"]
    )

    # --------------------------------------------------------
    # Sort chronologically
    #
    # IMPORTANT:
    # Do NOT sort by link first.
    # We need the final train/test split
    # to represent the actual timeline.
    # --------------------------------------------------------

    df = df.sort_values(
        "timestamp"
    ).reset_index(
        drop=True
    )

    # ========================================================
    # CLEAN NUMERIC FEATURES
    # ========================================================

    df["utilization_percent"] = (
        df["utilization_percent"]
        .clip(0, 100)
    )

    df["packet_loss_percent"] = (
        df["packet_loss_percent"]
        .clip(0, 100)
    )

    df["tx_mbps"] = (
        df["tx_mbps"]
        .fillna(0)
    )

    df["rx_mbps"] = (
        df["rx_mbps"]
        .fillna(0)
    )

    df["jitter_ms"] = (
        df["jitter_ms"]
        .fillna(0)
    )

    # --------------------------------------------------------
    # RTT
    # --------------------------------------------------------

    df["rtt_ms"] = (
        df.groupby("link")["rtt_ms"]
        .transform(
            lambda x:
            x.fillna(
                x.median()
            )
        )
    )

    df["rtt_ms"] = (
        df["rtt_ms"]
        .fillna(0)
    )

    # ========================================================
    # TIME-SERIES FEATURES
    # ========================================================

    # Previous utilization for each link
    df["utilization_lag1"] = (
        df.groupby("link")
        ["utilization_percent"]
        .shift(1)
    )

    # Utilization two samples ago
    df["utilization_lag2"] = (
        df.groupby("link")
        ["utilization_percent"]
        .shift(2)
    )

    # Change from previous observation
    df["utilization_change"] = (
        df["utilization_percent"]
        -
        df["utilization_lag1"]
    )

    # --------------------------------------------------------
    # Prediction target
    #
    # Predict the NEXT utilization value
    # for the SAME link.
    # --------------------------------------------------------

    df["future_utilization"] = (
        df.groupby("link")
        ["utilization_percent"]
        .shift(-1)
    )

    # --------------------------------------------------------
    # Remove rows where lag/target isn't available
    # --------------------------------------------------------

    df = df.dropna(
        subset=[
            "utilization_lag1",
            "utilization_lag2",
            "utilization_change",
            "future_utilization",
        ]
    )

    # --------------------------------------------------------
    # Target bounds
    # --------------------------------------------------------

    df["future_utilization"] = (
        df["future_utilization"]
        .clip(0, 100)
    )

    # --------------------------------------------------------
    # Sort globally again for chronological ML split
    # --------------------------------------------------------

    df = df.sort_values(
        "timestamp"
    ).reset_index(
        drop=True
    )

    # ========================================================
    # SAVE
    # ========================================================

    os.makedirs(
        "telemetry/data",
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    print()
    print("Phase 2 dataset created")
    print("-" * 38)

    print(
        f"File : {OUTPUT_FILE}"
    )

    print(
        f"Rows : {len(df)}"
    )

    print(
        f"Columns : {len(df.columns)}"
    )

    print()
    print("ML Features:")

    print(
        "- utilization_percent"
    )

    print(
        "- utilization_lag1"
    )

    print(
        "- utilization_lag2"
    )

    print(
        "- utilization_change"
    )

    print(
        "- rtt_ms"
    )

    print(
        "- jitter_ms"
    )

    print(
        "- packet_loss_percent"
    )

    print()
    print("ML Target:")
    print(
        "- future_utilization"
    )

    print()
    print("Sample:")
    print(
        df[
            [
                "link",
                "timestamp",
                "utilization_percent",
                "utilization_lag1",
                "utilization_lag2",
                "utilization_change",
                "future_utilization",
            ]
        ].head(10).to_string(
            index=False
        )
    )

    print("=" * 38)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    preprocess()