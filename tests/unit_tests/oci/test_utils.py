import pytest
from unittest.mock import MagicMock, mock_open, patch
from pycloudlib.oci.utils import get_subnet_id, parse_oci_config_from_env_vars
from pycloudlib.errors import PycloudlibError
from oci.retry import DEFAULT_RETRY_STRATEGY  # pylint: disable=E0611,E0401
import os
import toml


class TestGetSubnetId:
    @pytest.fixture
    @patch("pycloudlib.oci.utils.DEFAULT_RETRY_STRATEGY", None)
    def setup_environment(self):
        """
        Set up the test environment.

        This fixture is called before each test function execution.

        It mocks the network client and sets up the compartment ID and availability domain.
        """
        network_client = MagicMock()
        compartment_id = "compartment_id"
        availability_domain = "availability_domain"
        return network_client, compartment_id, availability_domain

    def test_get_subnet_id_fails_with_vcn_name_not_found(self, setup_environment):
        """Test get_subnet_id fails when VCN name is not found."""
        network_client, compartment_id, availability_domain = setup_environment
        network_client.list_vcns.return_value.data = []
        with pytest.raises(PycloudlibError, match="Unable to determine vcn name"):
            get_subnet_id(
                network_client,
                compartment_id,
                availability_domain,
                vcn_name="vcn_name",
            )

    def test_get_subnet_id_fails_with_multiple_vcns_found(self, setup_environment):
        """Test get_subnet_id fails when multiple VCNs with the same name are found."""
        network_client, compartment_id, availability_domain = setup_environment
        network_client.list_vcns.return_value.data = [MagicMock(), MagicMock()]
        with pytest.raises(PycloudlibError, match="Found multiple vcns with name"):
            get_subnet_id(
                network_client,
                compartment_id,
                availability_domain,
                vcn_name="vcn_name",
            )

    def test_get_subnet_id_fails_with_no_vcns_found(self, setup_environment):
        """Test get_subnet_id fails when no VCNs are found."""
        network_client, compartment_id, availability_domain = setup_environment
        network_client.list_vcns.return_value.data = []
        with pytest.raises(PycloudlibError, match="No VCNs found in compartment"):
            get_subnet_id(network_client, compartment_id, availability_domain)

    def test_get_subnet_id_fails_with_no_suitable_subnet_found(self, setup_environment):
        """Test get_subnet_id fails when no suitable subnet is found."""
        network_client, compartment_id, availability_domain = setup_environment
        vcn = MagicMock()
        vcn.id = "vcn_id"
        vcn.display_name = "vcn_name"
        network_client.list_vcns.return_value.data = [vcn]
        network_client.list_subnets.return_value.data = []
        with pytest.raises(PycloudlibError, match="Unable to find suitable subnet in VCN"):
            get_subnet_id(network_client, compartment_id, availability_domain)

    def test_get_subnet_id_fails_with_private_subnet(self, setup_environment):
        """Test get_subnet_id fails when the subnet is private."""
        network_client, compartment_id, availability_domain = setup_environment
        vcn = MagicMock()
        vcn.id = "vcn_id"
        vcn.display_name = "vcn_name"
        network_client.list_vcns.return_value.data = [vcn]
        subnet = MagicMock()
        subnet.prohibit_internet_ingress = True
        network_client.list_subnets.return_value.data = [subnet]
        with pytest.raises(PycloudlibError, match="Unable to find suitable subnet in VCN"):
            get_subnet_id(network_client, compartment_id, availability_domain)

    def test_get_subnet_id_fails_with_different_availability_domain(self, setup_environment):
        """Test get_subnet_id fails when the subnet is in a different availability domain."""
        network_client, compartment_id, availability_domain = setup_environment
        vcn = MagicMock()
        vcn.id = "vcn_id"
        vcn.display_name = "vcn_name"
        network_client.list_vcns.return_value.data = [vcn]
        subnet = MagicMock()
        subnet.prohibit_internet_ingress = False
        subnet.availability_domain = "different_availability_domain"
        network_client.list_subnets.return_value.data = [subnet]
        with pytest.raises(PycloudlibError, match="Unable to find suitable subnet in VCN"):
            get_subnet_id(network_client, compartment_id, availability_domain)

    def test_get_subnet_id_suceeds_without_vcn_name(self, setup_environment):
        """Test get_subnet_id suceeds without specifying a VCN name."""
        network_client, compartment_id, availability_domain = setup_environment
        vcn1 = MagicMock()
        vcn1.id = "vcn1_id"
        vcn1.display_name = "vcn1_name"
        vcn2 = MagicMock()
        vcn2.id = "vcn2_id"
        vcn2.display_name = "vcn2_name"
        network_client.list_vcns.return_value.data = [vcn1, vcn2]
        subnet = MagicMock()
        subnet.prohibit_internet_ingress = False
        subnet.availability_domain = None
        subnet.id = "subnet_id"
        network_client.list_subnets.return_value.data = [subnet]
        result = get_subnet_id(network_client, compartment_id, availability_domain)
        assert result == "subnet_id"
        # Ensure that list_subnets is called with the first VCN's ID, not the second
        network_client.list_subnets.assert_called_with(
            compartment_id, vcn_id="vcn1_id", retry_strategy=DEFAULT_RETRY_STRATEGY
        )

    def test_get_subnet_id_suceeds_with_vcn_name(self, setup_environment):
        """Test get_subnet_id suceeds with specifying a VCN name."""
        network_client, compartment_id, availability_domain = setup_environment
        vcn = MagicMock()
        vcn.id = "vcn_id"
        vcn.display_name = "vcn_name"
        network_client.list_vcns.return_value.data = [vcn]
        subnet = MagicMock()
        subnet.prohibit_internet_ingress = False
        subnet.availability_domain = None
        subnet.id = "subnet_id"
        network_client.list_subnets.return_value.data = [subnet]
        result = get_subnet_id(
            network_client,
            compartment_id,
            availability_domain,
            vcn_name="vcn_name",
        )
        assert result == "subnet_id"
        # Ensure that list_subnets is called with the specified VCN's ID
        network_client.list_subnets.assert_called_with(
            compartment_id, vcn_id="vcn_id", retry_strategy=DEFAULT_RETRY_STRATEGY
        )


class TestConfigPathFromEnv:
    @pytest.fixture(autouse=True)
    def clear_env(self):
        """Ensure environment variables are cleared before each test."""
        with patch.dict(os.environ, {}, clear=True):
            yield

    def test_no_env_var_returns_none(self):
        """Should return None if PYCLOUDLIB_OCI_CONFIG_FILE_PATH is not set."""
        assert parse_oci_config_from_env_vars() is None

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"region": "us-phoenix-1"}',
    )
    @patch(
        "toml.load",
        return_value={"region": "us-phoenix-1"},
    )
    def test_valid_config_file(self, mock_toml_load, mock_file):
        """Should correctly parse a valid OCI config file."""
        with patch.dict(os.environ, {"PYCLOUDLIB_OCI_CONFIG_FILE_PATH": "/path/to/config"}):
            result = parse_oci_config_from_env_vars()

        assert result == {"region": "us-phoenix-1"}
        mock_file.assert_called_once_with("/path/to/config")
        mock_toml_load.assert_called_once()

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="invalid toml data",
    )
    @patch(
        "toml.load",
        side_effect=toml.TomlDecodeError("Invalid TOML", "invalid toml data", 0),
    )
    def test_invalid_config_file_raises_error(
        self,
        mock_toml_load,
        mock_file,
    ):
        """Should raise PycloudlibError when the config file is invalid."""
        with patch.dict(os.environ, {"PYCLOUDLIB_OCI_CONFIG_FILE_PATH": "/path/to/config"}):
            with pytest.raises(PycloudlibError, match="Failed to load OCI config dict"):
                parse_oci_config_from_env_vars()

        mock_file.assert_called_once_with("/path/to/config")
        mock_toml_load.assert_called_once()

    @pytest.mark.parametrize("key_file_entry_in_config", [None, "/i/should/be/overridden"])
    @patch("toml.load", return_value={"region": "us-phoenix-1"})
    def test_key_file_path_overrides(
        self,
        mock_toml_load,
        key_file_entry_in_config,
        caplog,
    ):
        """
        This tests the usage of the PYCLOUDLIB_OCI_KEY_FILE_PATH environment variable to either
        override or add the key_file path to the config dict.

        Test cases:
            1. key_file entry not present in the config file
            2. key_file entry present in the config file
        """

        config_read_str = '{"region": "us-phoenix-1"'
        if key_file_entry_in_config:
            config_read_str += f', "key_file": "{key_file_entry_in_config}"'
        config_read_str += "}"
        with patch.dict(
            os.environ,
            {
                "PYCLOUDLIB_OCI_CONFIG_FILE_PATH": "/path/to/config",
                "PYCLOUDLIB_OCI_KEY_FILE_PATH": "/custom/key/path",
            },
        ), patch("builtins.open", new_callable=mock_open, read_data=config_read_str) as mock_file:
            result = parse_oci_config_from_env_vars()

        assert result == {
            "region": "us-phoenix-1",
            "key_file": "/custom/key/path",
        }, "Key file path not correctly overridden in config"
        mock_file.assert_called_once_with("/path/to/config")
        mock_toml_load.assert_called_once()
        if key_file_entry_in_config:
            assert (
                "Replacing existing key_file path in OCI config" in caplog.text
            ), "Key file path not replaced in config"
        else:
            assert (
                not "Replacing existing key_file path in OCI config" in caplog.text
            ), "Key file path replaced in config when not present"
        assert (
            "Using OCI key file path from environment variable $PYCLOUDLIB_OCI_KEY_FILE_PATH"
            in caplog.text
        ), "Key file path not read from environment variable"
