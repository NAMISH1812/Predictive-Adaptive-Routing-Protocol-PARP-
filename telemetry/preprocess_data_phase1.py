import pandas as pd
import os


INPUT_FILE = "telemetry/data/telemetry_processed.csv"
OUTPUT_FILE = "telemetry/data/ml_dataset.csv"


def preprocess():

    df = pd.read_csv(INPUT_FILE)

    print("Original dataset:")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    df = df.sort_values(
        ["link", "timestamp"]
    ).reset_index(drop=True)

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    df["utilization_percent"] = df[
        "utilization_percent"
    ].clip(lower=0, upper=100)

    df["packet_loss_percent"] = df[
        "packet_loss_percent"
    ].clip(lower=0, upper=100)

    df["rtt_ms"] = df["rtt_ms"].fillna(
        df.groupby("link")["rtt_ms"].transform("median")
    )

    df["jitter_ms"] = df["jitter_ms"].fillna(0)

    df["tx_mbps"] = df["tx_mbps"].fillna(0)
    df["rx_mbps"] = df["rx_mbps"].fillna(0)

    df["load_ratio"] = (
        df["utilization_percent"] / 100
    )

    df["congestion_score"] = (
        0.5 * df["load_ratio"]
        + 0.3 * (df["rtt_ms"] / df["rtt_ms"].max())
        + 0.2 * (df["jitter_ms"] / max(df["jitter_ms"].max(), 1))
    )

    df = df.dropna()

    os.makedirs(
        "telemetry/data",
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("======================================")
    print("Data preprocessing completed")
    print("======================================")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print()
    print("ML features:")
    print("- utilization_percent")
    print("- rtt_ms")
    print("- jitter_ms")
    print("- packet_loss_percent")
    print("- load_ratio")
    print()
    print("Target:")
    print("- congestion_score")


if __name__ == "__main__":
    preprocess()

