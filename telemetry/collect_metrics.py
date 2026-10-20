import csv
import os
import time
from datetime import datetime


# ============================================================
# PARP LINK CONFIGURATION
# ============================================================

LINKS = {
    "r1-r2": ("r1", "r1-eth1", 10),
    "r2-r4": ("r2", "r2-eth1", 10),
    "r1-r3": ("r1", "r1-eth2", 20),
    "r3-r4": ("r3", "r3-eth1", 20)
}


# ============================================================
# READ INTERFACE STATISTICS
# ============================================================

def read_stats(node, interface):
    """
    Read Linux network interface counters.

    Returns:
        tx_bytes
        rx_bytes
        tx_packets
        rx_packets
        tx_dropped
        rx_dropped
    """

    tx_bytes = int(
        node.cmd(
            f"cat /sys/class/net/{interface}/statistics/tx_bytes"
        ).strip()
    )

    rx_bytes = int(
        node.cmd(
            f"cat /sys/class/net/{interface}/statistics/rx_bytes"
        ).strip()
    )

    tx_packets = int(
        node.cmd(
            f"cat /sys/class/net/{interface}/statistics/tx_packets"
        ).strip()
    )

    rx_packets = int(
        node.cmd(
            f"cat /sys/class/net/{interface}/statistics/rx_packets"
        ).strip()
    )

    tx_dropped = int(
        node.cmd(
            f"cat /sys/class/net/{interface}/statistics/tx_dropped"
        ).strip()
    )

    rx_dropped = int(
        node.cmd(
            f"cat /sys/class/net/{interface}/statistics/rx_dropped"
        ).strip()
    )

    return (
        tx_bytes,
        rx_bytes,
        tx_packets,
        rx_packets,
        tx_dropped,
        rx_dropped
    )


# ============================================================
# RTT MEASUREMENT
# ============================================================

def get_rtt(h1, destination):
    """
    Measure end-to-end RTT from h1 to destination.

    Returns:
        RTT in milliseconds
        None if ping fails
    """

    result = h1.popen(
        [
            "ping",
            "-c",
            "1",
            "-W",
            "1",
            destination
        ]
    )

    output = result.communicate()[0].decode()

    for line in output.splitlines():

        if "time=" in line:

            try:

                value = (
                    line
                    .split("time=")[1]
                    .split()[0]
                )

                return float(value)

            except (ValueError, IndexError):

                return None

    return None


# ============================================================
# LIVE TELEMETRY - ONE SAMPLE
# ============================================================

def collect_once(net, previous_stats=None):
    """
    Collect one live telemetry sample.

    previous_stats contains the previous interface
    counters and is used to calculate utilization.

    Returns:
        rows
        current_stats
    """

    timestamp = datetime.now().isoformat()

    h1 = net.get("h1")

    # ------------------------------------------
    # Measure RTT
    # ------------------------------------------

    rtt = get_rtt(
        h1,
        "10.0.4.2"
    )

    current_stats = {}

    rows = []

    # ------------------------------------------
    # Read every monitored link
    # ------------------------------------------

    for link, (
        node_name,
        interface,
        capacity
    ) in LINKS.items():

        node = net.get(node_name)

        stats = read_stats(
            node,
            interface
        )

        current_stats[link] = stats

        # --------------------------------------
        # First sample
        # --------------------------------------

        if (
            previous_stats is None
            or link not in previous_stats
        ):

            tx_mbps = 0.0
            rx_mbps = 0.0
            utilization = 0.0
            packet_loss = 0.0

        else:

            previous = previous_stats[link]

            # ----------------------------------
            # Byte counters
            # ----------------------------------

            tx_bytes = stats[0]
            rx_bytes = stats[1]

            previous_tx_bytes = previous[0]
            previous_rx_bytes = previous[1]

            # ----------------------------------
            # Counter differences
            # ----------------------------------

            tx_delta = max(
                0,
                tx_bytes - previous_tx_bytes
            )

            rx_delta = max(
                0,
                rx_bytes - previous_rx_bytes
            )

            # ----------------------------------
            # Convert bytes to Mbps
            #
            # NOTE:
            # collect_once() is intended to be
            # called approximately once per
            # second.
            # ----------------------------------

            tx_mbps = (
                tx_delta * 8
            ) / 1_000_000

            rx_mbps = (
                rx_delta * 8
            ) / 1_000_000

            # ----------------------------------
            # Link utilization
            # ----------------------------------

            utilization = (
                tx_mbps / capacity
            ) * 100

            utilization = max(
                0.0,
                min(100.0, utilization)
            )

            # ----------------------------------
            # Packet loss
            # ----------------------------------

            tx_packets = stats[2]
            tx_dropped = stats[4]

            total_packets = (
                tx_packets + tx_dropped
            )

            if total_packets > 0:

                packet_loss = (
                    tx_dropped
                    / total_packets
                ) * 100

            else:

                packet_loss = 0.0

            packet_loss = max(
                0.0,
                min(100.0, packet_loss)
            )

        # --------------------------------------
        # Store telemetry row
        # --------------------------------------

        rows.append(
            {
                "timestamp": timestamp,
                "link": link,
                "node": node_name,
                "interface": interface,
                "capacity_mbps": capacity,

                "tx_bytes": stats[0],
                "rx_bytes": stats[1],

                "tx_packets": stats[2],
                "rx_packets": stats[3],

                "tx_dropped": stats[4],
                "rx_dropped": stats[5],

                "tx_mbps": tx_mbps,
                "rx_mbps": rx_mbps,

                "utilization_percent":
                    utilization,

                "packet_loss_percent":
                    packet_loss,

                "rtt_ms": rtt
            }
        )

    return rows, current_stats


# ============================================================
# JITTER CALCULATION
# ============================================================

def add_jitter(rows, previous_rtt):
    """
    Calculate RTT variation between consecutive
    telemetry samples.

    Jitter = absolute difference between current
    RTT and previous RTT.

    Returns:
        current_rtt
    """

    current_rtt = None

    # ------------------------------------------
    # Get current RTT
    # ------------------------------------------

    if rows:

        current_rtt = rows[0]["rtt_ms"]

    # ------------------------------------------
    # Calculate jitter
    # ------------------------------------------

    if (
        current_rtt is not None
        and previous_rtt is not None
    ):

        jitter = abs(
            current_rtt - previous_rtt
        )

    else:

        jitter = 0.0

    # ------------------------------------------
    # Add jitter to every link
    # ------------------------------------------

    for row in rows:

        row["jitter_ms"] = jitter

    return current_rtt


# ============================================================
# CONTINUOUS CSV TELEMETRY COLLECTOR
# ============================================================

def collect(
    net,
    duration=30,
    interval=1
):
    """
    Continuously collect telemetry and save it
    to telemetry/data/telemetry.csv.

    This function is useful for dataset generation.

    The adaptive controller should use collect_once()
    instead of running this function simultaneously.
    """

    os.makedirs(
        "telemetry/data",
        exist_ok=True
    )

    output_file = (
        "telemetry/data/telemetry.csv"
    )

    # ------------------------------------------
    # CSV output
    # ------------------------------------------

    with open(
        output_file,
        "w",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "timestamp",
                "link",
                "node",
                "interface",
                "capacity_mbps",
                "tx_bytes",
                "rx_bytes",
                "tx_packets",
                "rx_packets",
                "tx_dropped",
                "rx_dropped",
                "rtt_ms"
            ]
        )

        previous_stats = None

        start_time = time.time()

        while (
            time.time() - start_time
            < duration
        ):

            # ----------------------------------
            # Collect raw statistics
            # ----------------------------------

            rows, current_stats = (
                collect_once(
                    net,
                    previous_stats
                )
            )

            # ----------------------------------
            # Write rows to CSV
            # ----------------------------------

            for row in rows:

                writer.writerow(
                    [
                        row["timestamp"],
                        row["link"],
                        row["node"],
                        row["interface"],
                        row["capacity_mbps"],
                        row["tx_bytes"],
                        row["rx_bytes"],
                        row["tx_packets"],
                        row["rx_packets"],
                        row["tx_dropped"],
                        row["rx_dropped"],
                        row["rtt_ms"]
                    ]
                )

            file.flush()

            # ----------------------------------
            # Current counters become previous
            # counters for next iteration
            # ----------------------------------

            previous_stats = current_stats

            time.sleep(interval)


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":

    print("=" * 50)
    print(" PARP TELEMETRY MODULE")
    print("=" * 50)

    print()
    print("Configured links:")

    for link, (
        node,
        interface,
        capacity
    ) in LINKS.items():

        print(
            f"{link:8s} "
            f"{node:4s} "
            f"{interface:10s} "
            f"{capacity} Mbps"
        )

    print()
    print("Available functions:")
    print("- read_stats()")
    print("- get_rtt()")
    print("- collect_once()")
    print("- add_jitter()")
    print("- collect()")

    print()
    print(
        "This module must be executed "
        "inside a running Mininet topology."
    )

    print("=" * 50)