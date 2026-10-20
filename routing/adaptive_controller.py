import time
from datetime import datetime

from routing.parp_router import (
    load_model,
    predict_congestion,
    build_network,
    calculate_path
)

from telemetry.collect_metrics import (
    collect_once,
    add_jitter
)


# ============================================================
# ROUTE APPLICATION
# ============================================================

def apply_parp_route(net, path):

    r1 = net.get("r1")
    r4 = net.get("r4")

    # --------------------------------------------------------
    # Path 1
    # h1 -> r1 -> r2 -> r4 -> h2
    # --------------------------------------------------------

    if path == ["r1", "r2", "r4"]:

        print()
        print("Applying Path 1")
        print("h1 -> r1 -> r2 -> r4 -> h2")

        r1.cmd(
            "ip route replace "
            "10.0.4.0/24 via 10.0.12.2"
        )

        r4.cmd(
            "ip route replace "
            "10.0.1.0/24 via 10.0.24.1"
        )

        return True

    # --------------------------------------------------------
    # Path 2
    # h1 -> r1 -> r3 -> r4 -> h2
    # --------------------------------------------------------

    elif path == ["r1", "r3", "r4"]:

        print()
        print("Applying Path 2")
        print("h1 -> r1 -> r3 -> r4 -> h2")

        r1.cmd(
            "ip route replace "
            "10.0.4.0/24 via 10.0.13.2"
        )

        r4.cmd(
            "ip route replace "
            "10.0.1.0/24 via 10.0.34.1"
        )

        return True

    print()
    print("Unknown path:", path)

    return False


# ============================================================
# UPDATE UTILIZATION HISTORY
# ============================================================

def update_history(
    utilization_history,
    telemetry,
    max_history=3
):
    """
    Store current utilization after prediction.

    History format:

        link -> [t-2, t-1, t]

    The history is intentionally updated AFTER prediction
    so that lag1 and lag2 represent previous observations.
    """

    for link, data in telemetry.items():

        if link not in utilization_history:

            utilization_history[link] = []

        utilization_history[link].append(
            data["utilization_percent"]
        )

        # Keep only the latest observations
        if len(
            utilization_history[link]
        ) > max_history:

            utilization_history[link] = (
                utilization_history[link]
                [-max_history:]
            )


# ============================================================
# PRINT TELEMETRY
# ============================================================

def print_live_telemetry(telemetry):

    print()
    print("LIVE TELEMETRY")
    print("-" * 70)

    for link, data in telemetry.items():

        print(
            f"{link:8s} | "
            f"Utilization="
            f"{data['utilization_percent']:7.2f}% | "
            f"RTT="
            f"{data['rtt_ms']:7.2f} ms | "
            f"Jitter="
            f"{data['jitter_ms']:6.2f} ms | "
            f"Loss="
            f"{data['packet_loss_percent']:6.2f}%"
        )


# ============================================================
# PRINT PREDICTIONS
# ============================================================

def print_predictions(
    telemetry,
    predictions
):

    print()
    print(
        "PREDICTED FUTURE UTILIZATION"
    )

    print("-" * 70)

    for link, prediction in predictions.items():

        current = telemetry[link][
            "utilization_percent"
        ]

        print(
            f"{link:8s} | "
            f"Current="
            f"{current:7.2f}% | "
            f"Predicted="
            f"{prediction:7.2f}%"
        )


# ============================================================
# ADAPTIVE PARP CONTROLLER
# ============================================================

def run_controller(
    net,
    interval=1
):

    print()
    print("=" * 70)
    print(" PARP ADAPTIVE ROUTING CONTROLLER")
    print("=" * 70)

    # --------------------------------------------------------
    # Load trained model
    # --------------------------------------------------------

    model = load_model()

    print()
    print("Model loaded successfully.")

    print(
        f"Telemetry interval : "
        f"{interval} second"
    )

    # --------------------------------------------------------
    # Controller state
    # --------------------------------------------------------

    current_path = None

    previous_stats = None

    previous_rtt = None

    utilization_history = {}

    last_change_time = 0

    # --------------------------------------------------------
    # Route-change protection
    # --------------------------------------------------------

    cooldown = 10

    # Minimum cost improvement needed
    # before changing route.
    improvement_threshold = 0.10

    # ========================================================
    # INITIALIZE LIVE TELEMETRY
    # ========================================================

    print()
    print(
        "Initializing live telemetry..."
    )

    # --------------------------------------------------------
    # First sample establishes counter baseline
    # --------------------------------------------------------

    _, previous_stats = collect_once(
        net,
        None
    )

    time.sleep(interval)

    # --------------------------------------------------------
    # Second sample calculates utilization
    # --------------------------------------------------------

    rows, previous_stats = collect_once(
        net,
        previous_stats
    )

    previous_rtt = add_jitter(
        rows,
        None
    )

    print(
        "Live telemetry initialized."
    )

    # ========================================================
    # MAIN PARP LOOP
    # ========================================================

    while True:

        try:

            print()
            print("=" * 70)

            print(
                "PARP MONITORING CYCLE:",
                datetime.now().strftime(
                    "%H:%M:%S"
                )
            )

            print("=" * 70)

            # =================================================
            # STEP 1
            # Collect current telemetry
            # =================================================

            rows, current_stats = (
                collect_once(
                    net,
                    previous_stats
                )
            )

            previous_stats = current_stats

            # =================================================
            # STEP 2
            # Calculate jitter
            # =================================================

            previous_rtt = add_jitter(
                rows,
                previous_rtt
            )

            # =================================================
            # STEP 3
            # Convert rows into PARP telemetry dictionary
            # =================================================

            telemetry = {}

            for row in rows:

                telemetry[row["link"]] = {

                    "utilization_percent":
                        row[
                            "utilization_percent"
                        ],

                    "rtt_ms":
                        row["rtt_ms"]
                        if row["rtt_ms"] is not None
                        else 0.0,

                    "jitter_ms":
                        row["jitter_ms"],

                    "packet_loss_percent":
                        row[
                            "packet_loss_percent"
                        ]
                }

            # =================================================
            # STEP 4
            # Display live telemetry
            # =================================================

            print_live_telemetry(
                telemetry
            )

            # =================================================
            # STEP 5
            # Predict future utilization
            #
            # IMPORTANT:
            # Prediction happens BEFORE adding the current
            # value to history.
            # =================================================

            predictions = predict_congestion(
                model,
                telemetry,
                utilization_history
            )

            print_predictions(
                telemetry,
                predictions
            )

            # =================================================
            # STEP 6
            # NOW update utilization history
            # =================================================

            update_history(
                utilization_history,
                telemetry
            )

            # =================================================
            # STEP 7
            # Build predictive graph
            # =================================================

            graph = build_network(
                telemetry,
                predictions
            )

            # =================================================
            # STEP 8
            # Calculate best path using Dijkstra
            # =================================================

            new_path, new_cost = (
                calculate_path(
                    graph
                )
            )

            print()
            print(
                "CANDIDATE ROUTE"
            )

            print("-" * 70)

            print(
                "Candidate path:",
                " -> ".join(
                    new_path
                )
            )

            print(
                f"Candidate cost: "
                f"{new_cost:.4f}"
            )

            # =================================================
            # STEP 9
            # Establish initial route
            # =================================================

            if current_path is None:

                print()
                print(
                    "No PARP route currently "
                    "registered."
                )

                print(
                    "Establishing initial route..."
                )

                success = (
                    apply_parp_route(
                        net,
                        new_path
                    )
                )

                if success:

                    current_path = new_path

                    last_change_time = (
                        time.time()
                    )

                    print()
                    print(
                        "Initial PARP route "
                        "established."
                    )

                time.sleep(interval)

                continue

            # =================================================
            # STEP 10
            # Candidate route is same as current route
            # =================================================

            if new_path == current_path:

                print()
                print(
                    "DECISION: KEEP CURRENT ROUTE"
                )

                print(
                    "Current route:",
                    " -> ".join(
                        current_path
                    )
                )

                time.sleep(interval)

                continue

            # =================================================
            # STEP 11
            # Cooldown protection
            # =================================================

            elapsed = (
                time.time()
                - last_change_time
            )

            if elapsed < cooldown:

                remaining = (
                    cooldown
                    - elapsed
                )

                print()
                print(
                    "DECISION: KEEP CURRENT ROUTE"
                )

                print(
                    "Route-change cooldown "
                    "is active."
                )

                print(
                    f"Remaining: "
                    f"{remaining:.1f}s"
                )

                time.sleep(interval)

                continue

            # =================================================
            # STEP 12
            # Calculate cost of current route
            # =================================================

            current_cost = 0.0

            valid_current_path = True

            for i in range(
                len(current_path) - 1
            ):

                u = current_path[i]

                v = current_path[i + 1]

                if graph.has_edge(
                    u,
                    v
                ):

                    current_cost += (
                        graph[u][v]["weight"]
                    )

                else:

                    valid_current_path = False

                    break

            # -------------------------------------------------
            # If current path is invalid
            # -------------------------------------------------

            if not valid_current_path:

                current_cost = float(
                    "inf"
                )

            # =================================================
            # STEP 13
            # Compare routes
            # =================================================

            improvement = (
                current_cost
                - new_cost
            )

            print()
            print(
                "ROUTE COMPARISON"
            )

            print("-" * 70)

            print(
                "Current route:",
                " -> ".join(
                    current_path
                )
            )

            print(
                f"Current cost: "
                f"{current_cost:.4f}"
            )

            print(
                "Candidate route:",
                " -> ".join(
                    new_path
                )
            )

            print(
                f"Candidate cost: "
                f"{new_cost:.4f}"
            )

            print(
                f"Cost improvement: "
                f"{improvement:.4f}"
            )

            # =================================================
            # STEP 14
            # REROUTE
            # =================================================

            if (
                improvement
                > improvement_threshold
            ):

                print()
                print(
                    "DECISION: REROUTE"
                )

                print(
                    "Old route:",
                    " -> ".join(
                        current_path
                    )
                )

                print(
                    "New route:",
                    " -> ".join(
                        new_path
                    )
                )

                success = (
                    apply_parp_route(
                        net,
                        new_path
                    )
                )

                if success:

                    current_path = (
                        new_path
                    )

                    last_change_time = (
                        time.time()
                    )

                    print()
                    print(
                        "PARP route changed "
                        "successfully."
                    )

            # =================================================
            # STEP 15
            # KEEP CURRENT ROUTE
            # =================================================

            else:

                print()
                print(
                    "DECISION: KEEP CURRENT ROUTE"
                )

                print(
                    "Alternative route does "
                    "not provide sufficient "
                    "cost improvement."
                )

            # =================================================
            # STEP 16
            # Wait for next sample
            # =================================================

            time.sleep(
                interval
            )

        # ====================================================
        # CTRL+C
        # ====================================================

        except KeyboardInterrupt:

            print()
            print("=" * 70)
            print(
                "PARP controller stopped."
            )
            print("=" * 70)

            break

        # ====================================================
        # ERROR HANDLING
        # ====================================================

        except Exception as e:

            print()
            print("=" * 70)
            print(
                "PARP CONTROLLER ERROR"
            )
            print("=" * 70)

            print(
                type(e).__name__,
                ":",
                e
            )

            print(
                "Controller will retry..."
            )

            time.sleep(
                interval
            )