import pandas as pd


INPUT_FILE = "telemetry/data/telemetry.csv"
OUTPUT_FILE = "telemetry/data/telemetry_processed.csv"


df = pd.read_csv(INPUT_FILE)

df["timestamp"] = pd.to_datetime(df["timestamp"])

df = df.sort_values(
    ["link", "timestamp"]
)

df["time_diff"] = (
    df.groupby("link")["timestamp"]
    .diff()
    .dt.total_seconds()
)

df["tx_bytes_diff"] = (
    df.groupby("link")["tx_bytes"]
    .diff()
)

df["rx_bytes_diff"] = (
    df.groupby("link")["rx_bytes"]
    .diff()
)

df["tx_mbps"] = (
    df["tx_bytes_diff"]
    * 8
    / df["time_diff"]
    / 1_000_000
)

df["rx_mbps"] = (
    df["rx_bytes_diff"]
    * 8
    / df["time_diff"]
    / 1_000_000
)

df["utilization_percent"] = (
    df["tx_mbps"]
    / df["capacity_mbps"]
    * 100
)

df["packet_loss_percent"] = (
    df["tx_dropped"]
    /
    (
        df["tx_packets"]
        + df["tx_dropped"]
    )
    * 100
)

df["jitter_ms"] = (
    df.groupby("link")["rtt_ms"]
    .diff()
    .abs()
)

df = df.dropna(
    subset=[
        "tx_mbps",
        "rx_mbps",
        "rtt_ms",
        "jitter_ms"
    ]
)

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("======================================")
print("Telemetry processing completed")
print("======================================")
print(f"Input : {INPUT_FILE}")
print(f"Output: {OUTPUT_FILE}")
print()

print(
    df[
        [
            "timestamp",
            "link",
            "tx_mbps",
            "rx_mbps",
            "utilization_percent",
            "rtt_ms",
            "jitter_ms",
            "packet_loss_percent"
        ]
    ].to_string(index=False)
)