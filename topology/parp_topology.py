from mininet.net import Mininet
from mininet.node import Node
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

import os
import csv
import time
import re
from datetime import datetime


# ============================================================
# TELEMETRY CONFIGURATION
# ============================================================

LINKS = {
    "r1-r2": ("r1", "r1-eth1", 10),
    "r2-r4": ("r2", "r2-eth1", 10),
    "r1-r3": ("r1", "r1-eth2", 20),
    "r3-r4": ("r3", "r3-eth1", 20),
}


# ============================================================
# LINUX ROUTER
# ============================================================

class LinuxRouter(Node):

    def config(self, **params):
        super().config(**params)

        # Enable IPv4 forwarding
        self.cmd(
            "sysctl -w net.ipv4.ip_forward=1"
        )

    def terminate(self):

        # Disable IPv4 forwarding
        self.cmd(
            "sysctl -w net.ipv4.ip_forward=0"
        )

        super().terminate()


# ============================================================
# READ INTERFACE STATISTICS
# ============================================================

def read_interface_stats(node, interface):

    base = (
        f"/sys/class/net/{interface}/statistics"
    )

    def read_file(filename):

        output = node.cmd(
            f"cat {base}/{filename}"
        ).strip()

        try:
            return int(output)

        except ValueError:
            return 0

    return {
        "tx_bytes": read_file("tx_bytes"),
        "rx_bytes": read_file("rx_bytes"),
        "tx_packets": read_file("tx_packets"),
        "rx_packets": read_file("rx_packets"),
        "tx_dropped": read_file("tx_dropped"),
        "rx_dropped": read_file("rx_dropped"),
    }


# ============================================================
# RTT MEASUREMENT
# ============================================================

def get_rtt(h1):

    output = h1.cmd(
        "ping -c 1 -W 1 10.0.4.2"
    )

    match = re.search(
        r"time[=<]([\d.]+)\s*ms",
        output
    )

    if match:
        return float(match.group(1))

    # IMPORTANT:
    # A failed ping is NOT treated as 0 ms.
    return None


# ============================================================
# TELEMETRY COLLECTION
# ============================================================

def collect_telemetry(net, duration=20):

    output_file = (
        "telemetry/data/telemetry_processed.csv"
    )

    # Make sure directory exists
    os.makedirs(
        "telemetry/data",
        exist_ok=True
    )

    file_exists = os.path.exists(
        output_file
    )

    # --------------------------------------------------------
    # Initial interface counters
    # --------------------------------------------------------

    previous = {}

    for link, (
        node_name,
        interface,
        capacity
    ) in LINKS.items():

        node = net.get(node_name)

        previous[link] = (
            read_interface_stats(
                node,
                interface
            )
        )

    # --------------------------------------------------------
    # RTT history
    # --------------------------------------------------------

    previous_rtt = None

    # --------------------------------------------------------
    # Start message
    # --------------------------------------------------------

    print()
    print("--------------------------------------")
    print("PARP TELEMETRY COLLECTION")
    print("--------------------------------------")
    print(
        f"Duration : {duration} seconds"
    )
    print(
        f"Output   : {output_file}"
    )
    print("--------------------------------------")

    # --------------------------------------------------------
    # Open CSV
    # --------------------------------------------------------

    with open(
        output_file,
        "a",
        newline=""
    ) as f:

        fieldnames = [
            "timestamp",
            "link",
            "tx_mbps",
            "rx_mbps",
            "utilization_percent",
            "rtt_ms",
            "jitter_ms",
            "packet_loss_percent",
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        # Write header only once
        if not file_exists:
            writer.writeheader()

        # ----------------------------------------------------
        # Timing
        # ----------------------------------------------------

        start_time = time.time()

        previous_sample_time = (
            time.time()
        )

        # ----------------------------------------------------
        # Collection loop
        # ----------------------------------------------------

        while (
            time.time() - start_time
            < duration
        ):

            # Wait approximately one second
            time.sleep(1)

            # Actual current time
            current_sample_time = (
                time.time()
            )

            # Actual time between samples
            time_diff = (
                current_sample_time
                -
                previous_sample_time
            )

            previous_sample_time = (
                current_sample_time
            )

            # Prevent division by zero
            if time_diff <= 0:
                time_diff = 1.0

            timestamp = (
                datetime.now().isoformat()
            )

            # =================================================
            # RTT
            # =================================================

            rtt = get_rtt(
                net.get("h1")
            )

            # -------------------------------------------------
            # Handle RTT failures
            # -------------------------------------------------

            if rtt is None:

                if previous_rtt is not None:

                    rtt_for_csv = (
                        previous_rtt
                    )

                else:

                    rtt_for_csv = 0.0

                # Do not create fake
                # huge jitter values
                jitter = 0.0

            else:

                rtt_for_csv = rtt

                if previous_rtt is None:

                    jitter = 0.0

                else:

                    jitter = abs(
                        rtt
                        -
                        previous_rtt
                    )

                previous_rtt = rtt

            # =================================================
            # PROCESS EACH LINK
            # =================================================

            for link, (
                node_name,
                interface,
                capacity
            ) in LINKS.items():

                node = net.get(
                    node_name
                )

                # Current counters
                current = (
                    read_interface_stats(
                        node,
                        interface
                    )
                )

                # Previous counters
                old = previous[link]

                # ------------------------------------------------
                # Byte differences
                # ------------------------------------------------

                tx_bytes_diff = (
                    current["tx_bytes"]
                    -
                    old["tx_bytes"]
                )

                rx_bytes_diff = (
                    current["rx_bytes"]
                    -
                    old["rx_bytes"]
                )

                # Counter reset protection
                if tx_bytes_diff < 0:
                    tx_bytes_diff = 0

                if rx_bytes_diff < 0:
                    rx_bytes_diff = 0

                # ------------------------------------------------
                # Mbps
                # ------------------------------------------------

                tx_mbps = (
                    tx_bytes_diff
                    * 8
                    /
                    time_diff
                    /
                    1_000_000
                )

                rx_mbps = (
                    rx_bytes_diff
                    * 8
                    /
                    time_diff
                    /
                    1_000_000
                )

                # ------------------------------------------------
                # Link utilization
                # ------------------------------------------------

                utilization = (
                    tx_mbps
                    /
                    capacity
                ) * 100

                # Keep utilization between 0 and 100
                utilization = max(
                    0.0,
                    min(
                        100.0,
                        utilization
                    )
                )

                # ------------------------------------------------
                # Packet statistics
                # ------------------------------------------------

                tx_packets_diff = (
                    current["tx_packets"]
                    -
                    old["tx_packets"]
                )

                dropped_packets_diff = (
                    current["tx_dropped"]
                    -
                    old["tx_dropped"]
                )

                # Counter reset protection
                if tx_packets_diff < 0:
                    tx_packets_diff = 0

                if dropped_packets_diff < 0:
                    dropped_packets_diff = 0

                total_packets = (
                    tx_packets_diff
                    +
                    dropped_packets_diff
                )

                if total_packets > 0:

                    packet_loss = (
                        dropped_packets_diff
                        /
                        total_packets
                    ) * 100

                else:

                    packet_loss = 0.0

                # ------------------------------------------------
                # Write row
                # ------------------------------------------------

                writer.writerow({

                    "timestamp":
                        timestamp,

                    "link":
                        link,

                    "tx_mbps":
                        round(
                            tx_mbps,
                            4
                        ),

                    "rx_mbps":
                        round(
                            rx_mbps,
                            4
                        ),

                    "utilization_percent":
                        round(
                            utilization,
                            4
                        ),

                    "rtt_ms":
                        round(
                            rtt_for_csv,
                            4
                        ),

                    "jitter_ms":
                        round(
                            jitter,
                            4
                        ),

                    "packet_loss_percent":
                        round(
                            packet_loss,
                            4
                        ),
                })

                # ------------------------------------------------
                # Save current counters
                # ------------------------------------------------

                previous[link] = current

            # ----------------------------------------------------
            # Flush immediately
            # ----------------------------------------------------

            f.flush()

            # ----------------------------------------------------
            # Progress display
            # ----------------------------------------------------

            elapsed = int(
                time.time()
                -
                start_time
            )

            print(
                f"\rCollecting telemetry: "
                f"{elapsed}/{duration} seconds",
                end="",
                flush=True
            )

    print()
    print(
        "Telemetry collection complete."
    )
    print()


# ============================================================
# CUSTOM MININET CLI
# ============================================================

class PARPCLI(CLI):

    def do_collect_telemetry(
        self,
        line
    ):
        """
        Collect telemetry.

        Usage:
            collect_telemetry
            collect_telemetry 20
            collect_telemetry 30
        """

        args = line.split()

        # Default
        duration = 20

        # ----------------------------------------------------
        # Read duration
        # ----------------------------------------------------

        if args:

            try:

                duration = int(
                    args[0]
                )

            except ValueError:

                print(
                    "Usage: "
                    "collect_telemetry [duration]"
                )

                return

        # ----------------------------------------------------
        # Validate duration
        # ----------------------------------------------------

        if duration <= 0:

            print(
                "Duration must be "
                "greater than 0."
            )

            return

        # ----------------------------------------------------
        # Start collector
        # ----------------------------------------------------

        collect_telemetry(
            self.mn,
            duration
        )


# ============================================================
# CONFIGURE NETWORK INTERFACES
# ============================================================

def configure_interfaces(net):

    h1 = net.get("h1")
    h2 = net.get("h2")

    r1 = net.get("r1")
    r2 = net.get("r2")
    r3 = net.get("r3")
    r4 = net.get("r4")

    # ========================================================
    # H1
    # ========================================================

    h1.cmd(
        "ip addr flush dev h1-eth0"
    )

    h1.cmd(
        "ip addr add "
        "10.0.1.2/24 "
        "dev h1-eth0"
    )

    h1.cmd(
        "ip route replace "
        "default via 10.0.1.1"
    )

    # ========================================================
    # H2
    # ========================================================

    h2.cmd(
        "ip addr flush dev h2-eth0"
    )

    h2.cmd(
        "ip addr add "
        "10.0.4.2/24 "
        "dev h2-eth0"
    )

    h2.cmd(
        "ip route replace "
        "default via 10.0.4.1"
    )

    # ========================================================
    # R1
    # ========================================================

    r1.cmd(
        "ip addr flush dev r1-eth0"
    )

    r1.cmd(
        "ip addr flush dev r1-eth1"
    )

    r1.cmd(
        "ip addr flush dev r1-eth2"
    )

    # H1 <-> R1
    r1.cmd(
        "ip addr add "
        "10.0.1.1/24 "
        "dev r1-eth0"
    )

    # R1 <-> R2
    r1.cmd(
        "ip addr add "
        "10.0.12.1/24 "
        "dev r1-eth1"
    )

    # R1 <-> R3
    r1.cmd(
        "ip addr add "
        "10.0.13.1/24 "
        "dev r1-eth2"
    )

    # ========================================================
    # R2
    # ========================================================

    r2.cmd(
        "ip addr flush dev r2-eth0"
    )

    r2.cmd(
        "ip addr flush dev r2-eth1"
    )

    # R1 <-> R2
    r2.cmd(
        "ip addr add "
        "10.0.12.2/24 "
        "dev r2-eth0"
    )

    # R2 <-> R4
    r2.cmd(
        "ip addr add "
        "10.0.24.1/24 "
        "dev r2-eth1"
    )

    # ========================================================
    # R3
    # ========================================================

    r3.cmd(
        "ip addr flush dev r3-eth0"
    )

    r3.cmd(
        "ip addr flush dev r3-eth1"
    )

    # R1 <-> R3
    r3.cmd(
        "ip addr add "
        "10.0.13.2/24 "
        "dev r3-eth0"
    )

    # R3 <-> R4
    r3.cmd(
        "ip addr add "
        "10.0.34.1/24 "
        "dev r3-eth1"
    )

    # ========================================================
    # R4
    # ========================================================

    r4.cmd(
        "ip addr flush dev r4-eth0"
    )

    r4.cmd(
        "ip addr flush dev r4-eth1"
    )

    r4.cmd(
        "ip addr flush dev r4-eth2"
    )

    # R2 <-> R4
    r4.cmd(
        "ip addr add "
        "10.0.24.2/24 "
        "dev r4-eth0"
    )

    # R3 <-> R4
    r4.cmd(
        "ip addr add "
        "10.0.34.2/24 "
        "dev r4-eth1"
    )

    # R4 <-> H2
    r4.cmd(
        "ip addr add "
        "10.0.4.1/24 "
        "dev r4-eth2"
    )


# ============================================================
# CONFIGURE ROUTES
# ============================================================

def configure_routes(net):

    r1 = net.get("r1")
    r2 = net.get("r2")
    r3 = net.get("r3")
    r4 = net.get("r4")

    # ========================================================
    # Forward path
    #
    # H1 -> R1 -> R2 -> R4 -> H2
    # ========================================================

    r1.cmd(
        "ip route replace "
        "10.0.4.0/24 "
        "via 10.0.12.2"
    )

    r2.cmd(
        "ip route replace "
        "10.0.4.0/24 "
        "via 10.0.24.2"
    )

    # ========================================================
    # Return path
    #
    # H2 -> R4 -> R2 -> R1 -> H1
    # ========================================================

    r4.cmd(
        "ip route replace "
        "10.0.1.0/24 "
        "via 10.0.24.1"
    )

    r2.cmd(
        "ip route replace "
        "10.0.1.0/24 "
        "via 10.0.12.1"
    )

    # ========================================================
    # Path 2 routes
    #
    # R1 -> R3 -> R4
    #
    # These are installed so both paths are available.
    # The initial route remains Path 1.
    # ========================================================

    r3.cmd(
        "ip route replace "
        "10.0.4.0/24 "
        "via 10.0.34.2"
    )

    r3.cmd(
        "ip route replace "
        "10.0.1.0/24 "
        "via 10.0.13.1"
    )


# ============================================================
# CREATE NETWORK TOPOLOGY
# ============================================================

def create_topology():

    net = Mininet(
        controller=None,
        link=TCLink,
        autoSetMacs=True
    )

    # ========================================================
    # HOSTS
    # ========================================================

    h1 = net.addHost(
        "h1"
    )

    h2 = net.addHost(
        "h2"
    )

    # ========================================================
    # ROUTERS
    # ========================================================

    r1 = net.addHost(
        "r1",
        cls=LinuxRouter
    )

    r2 = net.addHost(
        "r2",
        cls=LinuxRouter
    )

    r3 = net.addHost(
        "r3",
        cls=LinuxRouter
    )

    r4 = net.addHost(
        "r4",
        cls=LinuxRouter
    )

    # ========================================================
    # LINKS
    # ========================================================

    # --------------------------------------------------------
    # H1 -> R1
    # --------------------------------------------------------

    net.addLink(
        h1,
        r1,
        bw=100,
        delay="2ms"
    )

    # --------------------------------------------------------
    # PATH 1
    #
    # H1 -> R1 -> R2 -> R4 -> H2
    #
    # 10 Mbps bottleneck
    # --------------------------------------------------------

    net.addLink(
        r1,
        r2,
        bw=10,
        delay="10ms"
    )

    net.addLink(
        r2,
        r4,
        bw=10,
        delay="10ms"
    )

    # --------------------------------------------------------
    # PATH 2
    #
    # H1 -> R1 -> R3 -> R4 -> H2
    #
    # 20 Mbps
    # --------------------------------------------------------

    net.addLink(
        r1,
        r3,
        bw=20,
        delay="5ms"
    )

    net.addLink(
        r3,
        r4,
        bw=20,
        delay="5ms"
    )

    # --------------------------------------------------------
    # R4 -> H2
    # --------------------------------------------------------

    net.addLink(
        r4,
        h2,
        bw=100,
        delay="2ms"
    )

    return net


# ============================================================
# MAIN
# ============================================================

def main():

    setLogLevel(
        "info"
    )

    # --------------------------------------------------------
    # Create topology
    # --------------------------------------------------------

    net = create_topology()

    # --------------------------------------------------------
    # Start Mininet
    # --------------------------------------------------------

    net.start()

    # --------------------------------------------------------
    # Configure interfaces
    # --------------------------------------------------------

    configure_interfaces(
        net
    )

    # --------------------------------------------------------
    # Configure routes
    # --------------------------------------------------------

    configure_routes(
        net
    )

    # --------------------------------------------------------
    # Connectivity test
    # --------------------------------------------------------

    info(
        "\n*** Testing connectivity "
        "h1 -> h2\n"
    )

    result = net.get(
        "h1"
    ).cmd(
        "ping -c 3 10.0.4.2"
    )

    print(result)

    # --------------------------------------------------------
    # Start custom CLI
    # --------------------------------------------------------

    PARPCLI(
        net
    )

    # --------------------------------------------------------
    # Stop network
    # --------------------------------------------------------

    net.stop()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()