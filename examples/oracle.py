#!/usr/bin/env python3
# This file is part of pycloudlib. See LICENSE file for license information.
"""Basic examples of various lifecycle with an OCI instance."""

import logging
import sys
from base64 import b64encode

import pycloudlib
from pycloudlib.cloud import NetworkingType

cloud_config = """#cloud-config
runcmd:
  - echo 'hello' > /home/ubuntu/example.txt
"""


def demo(
    availability_domain: str = None,
    compartment_id: str = None,
    vcn_name: str = None,
):
    """Show example of using the OCI library.

    Connects to OCI and launches released image. Then runs
    through a number of examples.
    """
    client = pycloudlib.OCI(
        "oracle-test",
        availability_domain=availability_domain,
        compartment_id=compartment_id,
        vcn_name=vcn_name,
    )
    instance = client.launch(
        image_id=client.get_image_id_from_name("noble-ipv6-with-cloud-init-df6638633"),
        # user_data=b64encode(cloud_config.encode()).decode(),
        networking_type=NetworkingType.IPV6,
    )
    instance.wait()
    print(instance.instance_data)
    print(instance.ip)
    instance.execute("cloud-init status --wait --long")
    print(instance.execute("cat /var/log/cloud-init.log"))
    print(instance.execute("cat /var/log/cloud-init-output.log"))

    print(instance.execute("/etc/default/grub.d/50-cloudimg-settings.cfg"))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) != 3:
        print(
            "No arguments passed via command line. "
            "Assuming values are set in pycloudlib configuration file."
        )
        demo()
    else:
        passed_availability_domain = sys.argv[1]
        passed_compartment_id = sys.argv[2]
        passed_vcn_name = sys.argv[3] if len(sys.argv) == 4 else None
        demo(
            passed_availability_domain, passed_compartment_id, passed_vcn_name
        )
