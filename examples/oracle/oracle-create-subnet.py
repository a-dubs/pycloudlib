#!/usr/bin/env python3
# This file is part of pycloudlib. See LICENSE file for license information.
"""Create an OCI subnet in a VCN using pycloudlib's OCI helper.

This minimal CLI reads networking type, privacy, and VCN name, then creates a
compatible subnet using OCI.create_subnet_in_vcn().

It expects your OCI configuration (availability domain, compartment, auth, etc.)
to be available via your pycloudlib config file and/or standard OCI config.
"""

import argparse
import logging
import sys

import pycloudlib
from pycloudlib.types import NetworkingConfig, NetworkingType


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an OCI subnet in a VCN")
    parser.add_argument(
        "--vcn-name",
        required=True,
        help="Name of the target VCN (must be unique in the compartment)",
    )
    parser.add_argument(
        "--subnet-name",
        required=False,
        help="Optional display name for the subnet. If omitted, a unique name is generated.",
    )
    parser.add_argument(
        "--networking-type",
        required=True,
        choices=[
            NetworkingType.IPV4.value,
            NetworkingType.IPV6.value,
            NetworkingType.DUAL_STACK.value,
        ],
        help="Networking type for the subnet: ipv4 | ipv6 | dual-stack",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="If set, create a private subnet (no public internet ingress)",
    )
    parser.add_argument(
        "--tag",
        default="pycl-oracle-subnet",
        help="Resource tag/prefix used for naming (default: pycl-oracle-subnet)",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO)
    args = parse_args(argv)

    # Build networking config
    net_cfg = NetworkingConfig(
        networking_type=NetworkingType(args.networking_type),
        private=bool(args.private),
    )

    # Use pycloudlib to connect to OCI; rely on configured credentials and region
    with pycloudlib.OCI(tag=args.tag, vcn_name=args.vcn_name) as client:
        subnet_id = client.create_subnet_in_vcn(
            vcn_name=args.vcn_name,
            networking_config=net_cfg,
            subnet_name=args.subnet_name,
        )
        print(subnet_id)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:])) 