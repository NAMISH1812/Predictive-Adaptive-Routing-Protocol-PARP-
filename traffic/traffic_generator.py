import subprocess
import argparse


def generate_traffic(destination, duration, bandwidth):

    print("--------------------------------------")
    print("PARP Traffic Generator")
    print("--------------------------------------")
    print(f"Destination : {destination}")
    print(f"Duration    : {duration} seconds")
    print(f"Bandwidth   : {bandwidth}")
    print("--------------------------------------")

    command = [
        "iperf3",
        "-c",
        destination,
        "-t",
        str(duration),
        "-b",
        bandwidth
    ]

    subprocess.run(command)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--destination",
        default="10.0.4.2"
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=30
    )

    parser.add_argument(
        "--bandwidth",
        default="5M"
    )

    args = parser.parse_args()

    generate_traffic(
        args.destination,
        args.duration,
        args.bandwidth
    )


if __name__ == "__main__":
    main()