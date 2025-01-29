import unittest
from unittest.mock import MagicMock, patch
from pycloudlib.oci.utils import get_subnet_id
from pycloudlib.errors import PycloudlibError


class TestGetSubnetId(unittest.TestCase):
    @patch("pycloudlib.oci.utils.DEFAULT_RETRY_STRATEGY", None)
    def setUp(self):
        self.network_client = MagicMock()
        self.compartment_id = "compartment_id"
        self.availability_domain = "availability_domain"

    def test_get_subnet_id_with_vcn_name_not_found(self):
        self.network_client.list_vcns.return_value.data = []
        with self.assertRaises(PycloudlibError) as context:
            get_subnet_id(
                self.network_client,
                self.compartment_id,
                self.availability_domain,
                vcn_name="vcn_name",
            )
        self.assertIn("Unable to determine vcn name", str(context.exception))

    def test_get_subnet_id_with_multiple_vcns_found(self):
        self.network_client.list_vcns.return_value.data = [MagicMock(), MagicMock()]
        with self.assertRaises(PycloudlibError) as context:
            get_subnet_id(
                self.network_client,
                self.compartment_id,
                self.availability_domain,
                vcn_name="vcn_name",
            )
        self.assertIn("Found multiple vcns with name", str(context.exception))

    def test_get_subnet_id_with_no_vcns_found(self):
        self.network_client.list_vcns.return_value.data = []
        with self.assertRaises(PycloudlibError) as context:
            get_subnet_id(self.network_client, self.compartment_id, self.availability_domain)
        self.assertIn("No VCNs found in compartment", str(context.exception))

    def test_get_subnet_id_with_no_suitable_subnet_found(self):
        vcn = MagicMock()
        vcn.id = "vcn_id"
        vcn.display_name = "vcn_name"
        self.network_client.list_vcns.return_value.data = [vcn]
        self.network_client.list_subnets.return_value.data = []
        with self.assertRaises(PycloudlibError) as context:
            get_subnet_id(self.network_client, self.compartment_id, self.availability_domain)
        self.assertIn("Unable to find suitable subnet in VCN", str(context.exception))

    def test_get_subnet_id_with_private_subnet(self):
        vcn = MagicMock()
        vcn.id = "vcn_id"
        vcn.display_name = "vcn_name"
        self.network_client.list_vcns.return_value.data = [vcn]
        subnet = MagicMock()
        subnet.prohibit_internet_ingress = True
        self.network_client.list_subnets.return_value.data = [subnet]
        with self.assertRaises(PycloudlibError) as context:
            get_subnet_id(self.network_client, self.compartment_id, self.availability_domain)
        self.assertIn("Unable to find suitable subnet in VCN", str(context.exception))

    def test_get_subnet_id_with_different_availability_domain(self):
        vcn = MagicMock()
        vcn.id = "vcn_id"
        vcn.display_name = "vcn_name"
        self.network_client.list_vcns.return_value.data = [vcn]
        subnet = MagicMock()
        subnet.prohibit_internet_ingress = False
        subnet.availability_domain = "different_availability_domain"
        self.network_client.list_subnets.return_value.data = [subnet]
        with self.assertRaises(PycloudlibError) as context:
            get_subnet_id(self.network_client, self.compartment_id, self.availability_domain)
        self.assertIn("Unable to find suitable subnet in VCN", str(context.exception))

    def test_get_subnet_id_success(self):
        vcn = MagicMock()
        vcn.id = "vcn_id"
        vcn.display_name = "vcn_name"
        self.network_client.list_vcns.return_value.data = [vcn]
        subnet = MagicMock()
        subnet.prohibit_internet_ingress = False
        subnet.availability_domain = self.availability_domain
        subnet.id = "subnet_id"
        self.network_client.list_subnets.return_value.data = [subnet]
        result = get_subnet_id(self.network_client, self.compartment_id, self.availability_domain)
        self.assertEqual(result, "subnet_id")

    def test_get_subnet_id_with_vcn_name_success(self):
        vcn = MagicMock()
        vcn.id = "vcn_id"
        vcn.display_name = "vcn_name"
        self.network_client.list_vcns.return_value.data = [vcn]
        subnet = MagicMock()
        subnet.prohibit_internet_ingress = False
        subnet.availability_domain = self.availability_domain
        subnet.id = "subnet_id"
        self.network_client.list_subnets.return_value.data = [subnet]
        result = get_subnet_id(
            self.network_client, self.compartment_id, self.availability_domain, vcn_name="vcn_name"
        )
        self.assertEqual(result, "subnet_id")


if __name__ == "__main__":
    unittest.main()
