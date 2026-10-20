import networkx as nx
import pandas as pd
import joblib

MODEL_FILE = "prediction/congestion_model.pkl"
TELEMETRY_FILE = "telemetry/data/ml_dataset.csv"

FEATURES = [
    "utilization_percent",
    "rtt_ms",
    "jitter_ms",
    "packet_loss_percent"
]


def load_model():
    return joblib.load(MODEL_FILE)


def load_latest_telemetry():
    df = pd.read_csv(TELEMETRY_FILE)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    latest_time = df["timestamp"].max()

    latest = df[
        df["timestamp"] == latest_time
    ].copy()

    return latest


def predict_congestion(model, telemetry):

    X = telemetry[FEATURES]

    telemetry["predicted_congestion"] = model.predict(X)

    return telemetry


def build_network(telemetry):

    graph = nx.Graph()

    links = {
        "r1-r2": ("r1", "r2"),
        "r2-r4": ("r2", "r4"),
        "r1-r3": ("r1", "r3"),
        "r3-r4": ("r3", "r4")
    }

    for link, (source, destination) in links.items():

        row = telemetry[
            telemetry["link"] == link
        ]

        if row.empty:
            continue

        congestion = float(
            row["predicted_congestion"].iloc[0]
        )

        utilization = float(
            row["utilization_percent"].iloc[0]
        )

        rtt = float(
            row["rtt_ms"].iloc[0]
        )

        packet_loss = float(
            row["packet_loss_percent"].iloc[0]
        )

        cost = (
            1
            + congestion
            + utilization / 100
            + rtt / 100
            + packet_loss / 100
        )

        graph.add_edge(
            source,
            destination,
            weight=cost,
            congestion=congestion,
            utilization=utilization,
            rtt=rtt,
            packet_loss=packet_loss
        )

    return graph


def calculate_path(graph):

    path = nx.shortest_path(
        graph,
        source="r1",
        target="r4",
        weight="weight"
    )

    cost = nx.path_weight(
        graph,
        path,
        weight="weight"
    )

    return path, cost


def apply_route(path, net):

    r1 = net.get("r1")
    r4 = net.get("r4")

    if path == ["r1", "r2", "r4"]:

        r1.cmd(
            "ip route replace 10.0.4.0/24 via 10.0.12.2"
        )

        r4.cmd(
            "ip route replace 10.0.1.0/24 via 10.0.24.1"
        )

        return "Path 1 applied"


    if path == ["r1", "r3", "r4"]:

        r1.cmd(
            "ip route replace 10.0.4.0/24 via 10.0.13.2"
        )

        r4.cmd(
            "ip route replace 10.0.1.0/24 via 10.0.34.1"
        )

        return "Path 2 applied"


    return "No matching route"


def main():

    print()
    print("======================================")
    print("       PARP ROUTING ENGINE")
    print("======================================")

    model = load_model()

    telemetry = load_latest_telemetry()

    telemetry = predict_congestion(
        model,
        telemetry
    )

    print()
    print("Predicted link conditions:")
    print()

    for _, row in telemetry.iterrows():

        print(
            f"{row['link']:8s} "
            f"Utilization={row['utilization_percent']:.2f}% "
            f"RTT={row['rtt_ms']:.2f} ms "
            f"Jitter={row['jitter_ms']:.2f} ms "
            f"Prediction={row['predicted_congestion']:.4f}"
        )

    graph = build_network(telemetry)

    path, cost = calculate_path(graph)

    print()
    print("--------------------------------------")
    print(
        f"Selected path : {' -> '.join(path)}"
    )
    print(
        f"Path cost     : {cost:.4f}"
    )
    print("--------------------------------------")

    print()
    print("Route selected successfully.")
    print("Actual route application requires")
    print("running this module from the Mininet")
    print("topology process.")
    print()


if __name__ == "__main__":
    main()