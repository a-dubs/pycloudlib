import pytest
import time

from pycloudlib.cloud import NetworkingConfig, NetworkingType
from pycloudlib.oci.cloud import OCI


@pytest.fixture
def oci_cloud():
    with OCI(
        tag="oracle-integrations-test-utils",
        vcn_name="ipv6-vcn",
    ) as oracle_cloud:
        yield oracle_cloud

IPV6_PUBLIC_SUBNET_ID = "ocid1.subnet.oc1.iad.aaaaaaaaofjoplcmjw4jtr22654bzkpo7od3jzij5z4phrhuhgtwrldvxihq"
DUAL_STACK_PUBLIC_SUBNET_ID = "ocid1.subnet.oc1.iad.aaaaaaaaz3ih5vu6z4bypvkte633vk6my4umrzhdunluikxuj2hvzbruy73a"
DUAL_STACK_PRIVATE_SUBNET_ID = "ocid1.subnet.oc1.iad.aaaaaaaaahhibjqn6x4re7t4ojegavini7wjxcrh3whkyq6ix5vfdx6om5aa"

@pytest.mark.parametrize(
    ["networking_type", "private", "expected_subnet_id"], 
    [
        pytest.param(
            NetworkingType.IPV6, 
            False, 
            IPV6_PUBLIC_SUBNET_ID, 
            id="ipv6_public"
        ),
        pytest.param(
            NetworkingType.DUAL_STACK, 
            True, 
            DUAL_STACK_PRIVATE_SUBNET_ID,
            id="dual_stack_private"
        ),
        pytest.param(
            NetworkingType.DUAL_STACK, 
            False, 
            DUAL_STACK_PUBLIC_SUBNET_ID,
            id="dual_stack_public"
        ),
    ]
)
def test_oci_subnet_finding(oci_cloud: OCI, networking_type, private, expected_subnet_id):
    """
    Test finding a subnet in OCI.
    """
    network_config: NetworkingConfig = NetworkingConfig(
        networking_type=networking_type,
        private=private,
    )
    subnet_id = oci_cloud.find_compatible_subnet(
        networking_config=network_config,
    )
    assert subnet_id == expected_subnet_id


import logging

logger = logging.getLogger(__name__)

@pytest.mark.parametrize(
    ["networking_type", "private", "expected_subnet_id"], 
    [
        pytest.param(
            NetworkingType.IPV6, 
            False, 
            IPV6_PUBLIC_SUBNET_ID, 
            id="ipv6_public"
        ),
        # pytest.param(
        #     NetworkingType.DUAL_STACK, 
        #     True, 
        #     DUAL_STACK_PRIVATE_SUBNET_ID,
        #     id="dual_stack_private"
        # ),
        pytest.param(
            NetworkingType.DUAL_STACK, 
            False, 
            DUAL_STACK_PUBLIC_SUBNET_ID,
            id="dual_stack_public"
        ),
    ]
)
def test_launch(
    oci_cloud: OCI, 
    networking_type, 
    private, 
    expected_subnet_id,
):
    """
    Test launching an OCI instance.
    """
    
    if networking_type == NetworkingType.IPV6:
        image_id = "ocid1.image.oc1.iad.aaaaaaaa7tx5y4i77joxxqgs55433jr6ckpcoi2gfta7dywvj4mezv2le2tq"
    else:
        image_id = oci_cloud.released_image("noble")
    networking_config: NetworkingConfig = NetworkingConfig(
        networking_type=networking_type,
        private=private,
    )
    with oci_cloud.launch(
        image_id=image_id,
        primary_network_config=networking_config,
    ) as instance:
        instance.wait()
        r = instance.execute("ip addr show")
        logger.info(r)
        assert r.ok
        r2 = instance.execute("cat /etc/netplan/50-cloud-init.yaml", use_sudo=True)
        logger.info(r2)
        assert r2.ok
        r3 = instance.execute("cat /run/net*")
        logger.info(r3)
