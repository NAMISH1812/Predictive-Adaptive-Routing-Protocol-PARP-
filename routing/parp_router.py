import os

import joblib
import networkx as nx
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_FILE = (
    "prediction/future_utilization_model.pkl"
)

TELEMETRY_FILE = (
    "telemetry/data/telemetry_processed.csv"
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


# ============================================================
# NETWORK TOPOLOGY
# ============================================================

LINKS = {
    "r1-r2": ("r1", "r2"),
    "r2-r4": ("r2", "r4"),
    "r1-r3": ("r1", "r3"),
    "r3-r4": ("r3", "r4"),
}


# ============================================================
# LOAD MODEL
# ============================================================

def load_model():

    if not os.path.exists(MODEL_FILE):

        raise FileNotFoundError(
            f"Model not found: {MODEL_FILE}"
        )

    return joblib.load(
        MODEL_FILE
    )


# ============================================================
# LOAD TELEMETRY
# ============================================================

def load_telemetry():

    if not os.path.exists(TELEMETRY_FILE):

        raise FileNotFoundError(
            f"Telemetry file not found: "
            f"{TELEMETRY_FILE}"
        )

    df = pd.read_csv(
        TELEMETRY_FILE
    )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"]
    )

    return df


# ============================================================
# PREPARE LATEST LINK FEATURES
# ============================================================

def get_latest_link_data(df):

    latest = {}

    # Process each link independently
    for link in LINKS:

        link_df = (
            df[df["link"] == link]
            .sort_values("timestamp")
            .copy()
        )

        if len(link_df) < 3:
            continue

        # Last three observations
        last = link_df.iloc[-1]
        previous = link_df.iloc[-2]
        previous2 = link_df.iloc[-3]

        row = {
            "utilization_percent":
                last["utilization_percent"],

            "utilization_lag1":
                previous["utilization_percent"],

            "utilization_lag2":
                previous2["utilization_percent"],

            "utilization_change":
                (
                    last["utilization_percent"]
                    -
                    previous["utilization_percent"]
                ),

            "rtt_ms":
                last["rtt_ms"],

            "jitter_ms":
                last["jitter_ms"],

            "packet_loss_percent":
                last["packet_loss_percent"],
        }

        latest[link] = row

    return latest


# ============================================================
# PREDICT FUTURE UTILIZATION
# ============================================================

def predict_utilization(
    model,
    latest_data
):

    predictions = {}

    for link, data in latest_data.items():

        X = pd.DataFrame(
            [data],
            columns=FEATURES
        )

        prediction = model.predict(X)[0]

        # Utilization must be 0-100%
        prediction = max(
            0.0,
            min(
                100.0,
                float(prediction)
            )
        )

        predictions[link] = prediction

    return predictions


# ============================================================
# CALCULATE LINK COST
# ============================================================

def calculate_link_cost(
    link_data,
    predicted_utilization
):

    rtt = float(
        link_data["rtt_ms"]
    )

    jitter = float(
        link_data["jitter_ms"]
    )

    packet_loss = float(
        link_data["packet_loss_percent"]
    )

    # --------------------------------------------------------
    # Predictive cost
    #
    # Higher future utilization
    # -> higher cost
    #
    # Higher RTT
    # -> higher cost
    #
    # Higher jitter
    # -> higher cost
    #
    # Higher packet loss
    # -> higher cost
    # --------------------------------------------------------

    cost = (
        1.0
        +
        predicted_utilization / 100.0
        +
        rtt / 100.0
        +
        jitter / 100.0
        +
        packet_loss / 100.0
    )

    return cost


# ============================================================
# BUILD NETWORK GRAPH
# ============================================================

def build_graph(
    latest_data,
    predictions
):

    graph = nx.Graph()

    for link, (
        source,
        destination
    ) in LINKS.items():

        if link not in latest_data:
            continue

        cost = calculate_link_cost(
            latest_data[link],
            predictions[link]
        )

        graph.add_edge(
            source,
            destination,
            weight=cost,
            link=link
        )

    return graph


# ============================================================
# RUN DIJKSTRA
# ============================================================

def find_best_path(graph):

    path = nx.shortest_path(
        graph,
        source="r1",
        target="r4",
        weight="weight"
    )

    total_cost = nx.shortest_path_length(
        graph,
        source="r1",
        target="r4",
        weight="weight"
    )

    return path, total_cost


# ============================================================
# MAIN PARP ROUTING ANALYSIS
# ============================================================

def run_parp():

    print("=" * 60)
    print("PARP - PREDICTIVE ADAPTIVE ROUTING")
    print("=" * 60)

    # --------------------------------------------------------
    # Load model
    # --------------------------------------------------------

    print("\nLoading trained model...")

    model = load_model()

    print(
        "Model loaded successfully."
    )

    # --------------------------------------------------------
    # Load telemetry
    # --------------------------------------------------------

    print(
        "\nLoading latest telemetry..."
    )

    df = load_telemetry()

    print(
        f"Telemetry rows: {len(df)}"
    )

    # --------------------------------------------------------
    # Latest link information
    # --------------------------------------------------------

    latest_data = get_latest_link_data(
        df
    )

    # --------------------------------------------------------
    # Predict future utilization
    # --------------------------------------------------------

    predictions = predict_utilization(
        model,
        latest_data
    )

    # --------------------------------------------------------
    # Display predictions
    # --------------------------------------------------------

    print()
    print("-" * 60)
    print("LINK PREDICTIONS")
    print("-" * 60)

    for link in LINKS:

        if link not in latest_data:
            continue

        current = (
            latest_data[link]
            ["utilization_percent"]
        )

        predicted = (
            predictions[link]
        )

        print(
            f"{link:8s} | "
            f"Current: {current:7.2f}% | "
            f"Predicted: {predicted:7.2f}%"
        )

    # --------------------------------------------------------
    # Calculate costs
    # --------------------------------------------------------

    print()
    print("-" * 60)
    print("PREDICTIVE LINK COSTS")
    print("-" * 60)

    costs = {}

    for link in LINKS:

        if link not in latest_data:
            continue

        cost = calculate_link_cost(
            latest_data[link],
            predictions[link]
        )

        costs[link] = cost

        print(
            f"{link:8s} | "
            f"Cost: {cost:.4f}"
        )

    # --------------------------------------------------------
    # Build graph
    # --------------------------------------------------------

    graph = build_graph(
        latest_data,
        predictions
    )

    # --------------------------------------------------------
    # Find route
    # --------------------------------------------------------

    path, total_cost = find_best_path(
        graph
    )

    # --------------------------------------------------------
    # Display route
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("DIJKSTRA ROUTING RESULT")
    print("=" * 60)

    print(
        "Route: "
        +
        " -> ".join(path)
    )

    print(
        f"Total cost: {total_cost:.4f}"
    )

    # --------------------------------------------------------
    # Determine links in route
    # --------------------------------------------------------

    selected_links = []

    for i in range(
        len(path) - 1
    ):

        a = path[i]
        b = path[i + 1]

        link_name = (
            f"{a}-{b}"
        )

        reverse_name = (
            f"{b}-{a}"
        )

        if link_name in LINKS:
            selected_links.append(
                link_name
            )

        elif reverse_name in LINKS:
            selected_links.append(
                reverse_name
            )

    print(
        "Selected links: "
        +
        " -> ".join(
            selected_links
        )
    )

    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    run_parp()