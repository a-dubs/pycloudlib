# This file is part of pycloudlib. See LICENSE file for license information.
"""Utilities for OCI images and instances."""

import logging
import time
from typing import TYPE_CHECKING, Dict, Optional

from oci.retry import DEFAULT_RETRY_STRATEGY  # pylint: disable=E0611,E0401

from pycloudlib.errors import PycloudlibError, PycloudlibTimeoutError

if TYPE_CHECKING:
    import oci


log = logging.getLogger(__name__)


def wait_till_ready(
    func,
    current_data,
    desired_state,
    sleep_seconds=1000,
    func_kwargs: Optional[Dict[str, str]] = None,
):
    """Wait until the results of function call reach a desired lifecycle state.

    Args:
        func: The function to call
        current_data: Structure containing the initial id and lifecycle state
        desired_state: Desired value of "lifecycle_state"
        sleep_seconds: How long to wait in seconds
        func_kwargs: Dictionary with keyword arguments to pass to the function
    Returns:
        The updated version of the current_data
    Raises:
        PycloudlibTimeoutError: If the desired state is not reached in time
    """
    if func_kwargs is None:
        func_kwargs = {}

    for _ in range(sleep_seconds):
        current_data = func(current_data.id, **func_kwargs).data
        if current_data.lifecycle_state == desired_state:
            return current_data
        time.sleep(1)
    raise PycloudlibTimeoutError(
        "Expected {} state, but found {} after waiting {} seconds. "
        "Check OCI console for more details".format(
            desired_state, current_data.lifecycle_state, sleep_seconds
        )
    )


def get_subnet_id(
    network_client: "oci.core.VirtualNetworkClient",
    compartment_id: str,
    availability_domain: str,
    vcn_name: Optional[str] = None,
    *,
    retry_strategy=DEFAULT_RETRY_STRATEGY,
) -> str:
    """Get a subnet id linked to `availability_domain`.

    From specified compartment select the first subnet linked to
    `availability_domain` or the first one.

    Args:
        network_client: Instance of VirtualNetworkClient.
        compartment_id: Compartment where the subnet has to belong
        availability_domain: Domain to look for subnet id in.
        vcn_name: Exact name of the VCN to use. If not provided, the newest
            VCN in the given compartment will be used.
        retry_strategy: A retry strategy to apply to the API calls
    Returns:
        id of the subnet selected
    Raises:
        `Exception` if unable to determine `subnet_id` for
        `availability_domain`
    """
    if vcn_name is not None:  # if vcn_name specified, use that vcn
        vcns = network_client.list_vcns(
            compartment_id,
            display_name=vcn_name,
            retry_strategy=retry_strategy,
        ).data
        if len(vcns) == 0:
            raise PycloudlibError(f"Unable to determine vcn name: {vcn_name}")
        if len(vcns) > 1:
            raise PycloudlibError(f"Found multiple vcns with name: {vcn_name}")
    else:  # if no vcn_name specified, use most recently created vcn
        vcns = network_client.list_vcns(compartment_id, retry_strategy=retry_strategy).data
        if len(vcns) == 0:
            raise PycloudlibError("No VCNs found in compartment")
    vcn_id = vcns[0].id
    chosen_vcn_name = vcns[0].display_name

    subnets = network_client.list_subnets(
        compartment_id, vcn_id=vcn_id, retry_strategy=retry_strategy
    ).data
    subnet_id = None
    for subnet in subnets:
        if subnet.prohibit_internet_ingress:  # skip subnet if it's private
            log.debug(
                "Ignoring private subnet: %s [id: %s]",
                subnet.display_name,
                subnet.id,
            )
            continue
        if subnet.availability_domain and subnet.availability_domain != availability_domain:
            log.debug(
                "Ignoring public subnet in different availability domain: %s [id: %s]",
                subnet.display_name,
                subnet.id,
            )
            continue
        log.info("Using public subnet: %s [id: %s]", subnet.display_name, subnet.id)
        subnet_id = subnet.id
        break
    if not subnet_id:
        raise PycloudlibError(f"Unable to find suitable subnet in VCN {chosen_vcn_name}")
    return subnet_id
