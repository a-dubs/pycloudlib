#!/usr/bin/env python3
# This file is part of pycloudlib. See LICENSE file for license information.
"""Basic examples of various lifecycle with an OCI instance."""

from datetime import datetime
import json
import logging
import sys
import time

import pytest

import pycloudlib
from pycloudlib.oci.instance import OciInstance
from typing import Generator
import logging
import threading

logger = logging.getLogger(__name__)

EXISTING_INSTANCE_IDS = [
    # add the OCIDs of the instances you want to use for testing here
]

# change this to either "class" or "module" as you see fit
@pytest.fixture(scope="module")
def cluster() -> Generator[list[OciInstance], None, None]:
    """
    Launch a cluster of BM instances and yield them.
    """ 

    with pycloudlib.OCI(
        "pycl-oracle-cluster-test",
        # use the already created "mofed-vcn" for cluster testing
        vcn_name="mofed-vcn" # THIS WILL OVERRIDE THE VCN_NAME IN THE CONFIG FILE
    ) as client:
        if EXISTING_INSTANCE_IDS:
            instances = [client.get_instance(instance_id) for instance_id in EXISTING_INSTANCE_IDS]
            yield instances
        else:
            # create_compute_cluster already calls wait() on the instances
            # so once this function returns, the instances are ready
            instances = client.create_compute_cluster(
                # if you create a custom image, specify its OCID here
                image_id=client.released_image("noble"), 
                instance_count=2,
            )
            yield instances


class TestOracleClusterBasic:
    def test_basic_ping_on_private_ips(self, cluster: list[OciInstance]):
        """
        Verifies that the instances in the cluster can reach each other on their private IPs.
        """
        # get the private ips of the instances
        private_ips = [instance.private_ip for instance in cluster]
        # try to ping each instance from each other instance at their private ip
        for instance in cluster:
            for private_ip in private_ips:
                if private_ip != instance.private_ip:
                    logger.info(f"Pinging {private_ip} from {instance.private_ip}")
                    # ping once with a timeout of 5 seconds
                    r = instance.execute(f"ping -c 1 -W 5 {private_ip}")
                    assert r.ok, f"Failed to ping {private_ip} from {instance.private_ip}"
                    logger.info(f"Successfully pinged {private_ip} from {instance.private_ip}")


def setup_mofed_iptables_rules(instance: OciInstance):
    # Update the cloud.cfg file to set preserve_hostname to true
    instance.execute("sed -i 's/preserve_hostname: false/preserve_hostname: true/' /etc/cloud/cloud.cfg")
    # Backup the existing iptables rules
    backup_file = f"/etc/iptables/rules.v4.bak.{datetime.now().strftime('%F-%T')}"
    instance.execute(f"cp -v /etc/iptables/rules.v4 {backup_file}")
    # Overwrite the iptables rules with the new configuration
    rules = """
    *filter
    :INPUT ACCEPT [0:0]
    :FORWARD ACCEPT [0:0]
    :OUTPUT ACCEPT [0:0]

    # Allow all traffic on ens300f1np1 and ens800f0np0
    -A INPUT -i ens300f1np1 -j ACCEPT
    -A OUTPUT -o ens300f1np1 -j ACCEPT
    -A INPUT -i ens800f0np0 -j ACCEPT
    -A OUTPUT -o ens800f0np0 -j ACCEPT

    # Re-add REJECT rule for ens300f0np0
    -A INPUT -i ens300f0np0 -p icmp -j REJECT --reject-with icmp-host-prohibited
    -A OUTPUT -o ens300f0np0 -p icmp -j REJECT --reject-with icmp-host-prohibited

    COMMIT
    """
    instance.execute(f"cat > /etc/iptables/rules.v4 << 'EOL' {rules} EOL")
    # Restore the new iptables rules
    instance.execute("iptables-restore < /etc/iptables/rules.v4")
    # Log the current iptables rules with line numbers
    iptables_out = instance.execute("iptables -L -v -n --line-numbers")
    logger.info("iptables rules: %s", iptables_out.stdout)
    return instance


def ensure_image_is_rdma_ready(instance: OciInstance):
    r = instance.execute("ibstatus")
    if not r.stdout or not r.ok:
        logger.info("Infiniband status: %s", r.stdout + "\n" + r.stderr)
        pytest.skip("The image beiing used is not RDMA ready")


class TestOracleClusterRdma:
    @pytest.fixture(scope="class")
    def mofed_cluster(self, cluster: list[OciInstance]) -> Generator[list[OciInstance], None, None]:
        """
        Custom fixture to configure the instances in the cluster for RDMA testing.
        
        This fixture will:
        - Ensure the image being used is RDMA ready
        - Create a secondary VNIC on the private subnet for each instance in the cluster
        - Configure the secondary VNIC for RDMA usage
        - Set up the necessary iptables rules for RDMA usage on each instance's secondary NIC
        """
        ensure_image_is_rdma_ready(cluster[0])
        for instance in cluster:
            if instance.secondary_vnic_private_ip:
                logger.info(
                    "Instance %s already has a secondary VNIC, not attaching one.", instance.name
                )
                continue
            logger.info("Creating a secondary VNIC on instance %s", instance.name)
            # create a secondary VNIC on the 2nd vnic on the private subnet for RDMA usage
            instance.add_network_interface(
                nic_index=1,
                subnet_name="private subnet-mofed-vcn", # use the private subnet for mofed testing
            )
            instance.configure_secondary_vnic()
            setup_mofed_iptables_rules(instance)
            
        yield cluster
    
    def test_basic_ping_on_new_rdma_ips(
        self,
        mofed_cluster: list[OciInstance],
    ):
        # get the private ips of the instances
        rdma_ips = [instance.secondary_vnic_private_ip for instance in mofed_cluster]
        # try to ping each instance from each other instance at their private ip
        for instance in mofed_cluster:
            for rdma_ip in rdma_ips:
                if rdma_ip != instance.secondary_vnic_private_ip:
                    logger.info(f"Pinging {rdma_ip} from {instance.secondary_vnic_private_ip}")
                    # ping once with a timeout of 5 seconds
                    r = instance.execute(f"ping -c 1 -W 5 {rdma_ip}")
                    assert r.ok, f"Failed to ping {rdma_ip} from {instance.secondary_vnic_private_ip}"
                    logger.info(f"Successfully pinged {rdma_ip} from {instance.secondary_vnic_private_ip}")
            
    def test_rping(
        self,
        mofed_cluster: list[OciInstance],
    ):
        server_instance = mofed_cluster[0]
        client_instance = mofed_cluster[1]

        def start_server():
            # start the rping server on the first instance
            server_instance.execute(f"rping -s -a {server_instance.secondary_vnic_private_ip} -v &")

        server_thread = threading.Thread(target=start_server)
        server_thread.start()

        # Wait for rping server to start
        time.sleep(5)
        # start the rping client on the second instance (only send 10 packets so it doesn't hang)
        r = client_instance.execute(f"rping -c -a {server_instance.secondary_vnic_private_ip} -C 10 -v")
        logger.info("rping output: %s", r.stdout)
        assert r.ok, "Failed to run rping"

    def test_ucmatose(
        self,
        mofed_cluster: list[OciInstance],
    ):
        server_instance = mofed_cluster[0]
        client_instance = mofed_cluster[1]

        def start_server():
            # start the rping server on the first instance
            server_instance.execute(f"ucmatose &")

        server_thread = threading.Thread(target=start_server)
        server_thread.start()

        # Wait for server to start
        time.sleep(5)
        # start the client on the second instance (only send 10 packets so it doesn't hang)
        r = client_instance.execute(f"ucmatose -s {server_instance.secondary_vnic_private_ip}")
        logger.info("ucmatose output: %s", r.stdout)
        assert r.ok, "Failed to run ucmatose"

    def test_ucx_perftest_lat_one_node(
        self,
        mofed_cluster: list[OciInstance],
    ):
        server_instance = mofed_cluster[0]
        # ucx_perftest only works within a single instance on all MOFED stacks right now, so this
        # being 0 is intentional. (Will adjust if Oracle provides config info to resolve this)
        client_instance = mofed_cluster[0]

        def start_server():
            # start the rping server on the first instance
            server_instance.execute(f"ucx_perftest -c 0 &")

        server_thread = threading.Thread(target=start_server)
        server_thread.start()

        # Wait for server to start
        time.sleep(5)
        # start the client on the second instance (only send 10 packets so it doesn't hang)
        r = client_instance.execute(f"ucx_perftest {server_instance.secondary_vnic_private_ip} -t tag_lat -c 1")
        logger.info("ucx_perftest output: %s", r.stdout)
        assert r.ok, "Failed to run ucx_perftest"


    def test_ucx_perftest_bw_one_node(
        self,
        mofed_cluster: list[OciInstance],
    ):
        server_instance = mofed_cluster[0]
        # ucx_perftest only works within a single instance on all MOFED stacks right now, so this
        # being 0 is intentional. (Will adjust if Oracle provides config info to resolve this)
        client_instance = mofed_cluster[0]

        def start_server():
            # start the rping server on the first instance
            server_instance.execute(f"ucx_perftest -c 0 &")

        server_thread = threading.Thread(target=start_server)
        server_thread.start()

        # Wait for server to start
        time.sleep(5)
        # start the client on the second instance (only send 10 packets so it doesn't hang)
        r = client_instance.execute(f"ucx_perftest {server_instance.secondary_vnic_private_ip} -t tag_bw -c 1")
        logger.info("ucx_perftest output: %s", r.stdout)
        assert r.ok, "Failed to run ucx_perftest"
