"""Test cloud class integration with enhanced configuration system."""

import pytest
from io import StringIO
from unittest.mock import patch, MagicMock

from pycloudlib.ec2.cloud import EC2


class TestCloudConfigIntegration:
    """Test integration of cloud classes with the new configuration system."""

    @patch('pycloudlib.ec2.util._get_session')
    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_ec2_config_toml_only(self, mock_ssh_keys, mock_get_session):
        """Test EC2 initialization with TOML config only."""
        # Mock AWS session
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session.resource.return_value = MagicMock()
        mock_session.region_name = "us-west-2"
        mock_get_session.return_value = mock_session
        
        # Mock SSH keys
        mock_ssh_keys.return_value = MagicMock()
        
        config_content = '''
[ec2]
region = "us-west-2"
profile = "default"
public_key_path = "/fake/path"
'''
        
        ec2 = EC2('test', config_file=StringIO(config_content))
        
        assert ec2.config['region'] == 'us-west-2'
        assert ec2.config['profile'] == 'default'
        assert ec2.config['public_key_path'] == '/fake/path'

    @patch('pycloudlib.ec2.util._get_session')
    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_ec2_config_constructor_override(self, mock_ssh_keys, mock_get_session):
        """Test EC2 initialization with constructor parameters overriding TOML."""
        # Mock AWS session
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session.resource.return_value = MagicMock()
        mock_session.region_name = "us-east-1"  # Different from TOML
        mock_get_session.return_value = mock_session
        
        # Mock SSH keys
        mock_ssh_keys.return_value = MagicMock()
        
        config_content = '''
[ec2]
region = "us-west-2"
profile = "default"
public_key_path = "/fake/path"
'''
        
        # Constructor parameters should override TOML
        ec2 = EC2(
            'test', 
            config_file=StringIO(config_content),
            region="us-east-1",  # Override TOML region
            access_key_id="AKIATEST"  # New parameter not in TOML
        )
        
        # Verify merging worked correctly
        assert ec2.config['region'] == 'us-east-1'  # Overridden
        assert ec2.config['profile'] == 'default'  # From TOML
        assert ec2.config['public_key_path'] == '/fake/path'  # From TOML
        assert ec2.config['access_key_id'] == 'AKIATEST'  # From constructor

    @patch('pycloudlib.ec2.util._get_session')
    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_ec2_config_constructor_none_values_ignored(self, mock_ssh_keys, mock_get_session):
        """Test that None values in constructor don't override TOML."""
        # Mock AWS session
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session.resource.return_value = MagicMock()
        mock_session.region_name = "us-west-2"
        mock_get_session.return_value = mock_session
        
        # Mock SSH keys
        mock_ssh_keys.return_value = MagicMock()
        
        config_content = '''
[ec2]
region = "us-west-2"
profile = "default"
'''
        
        # None values should not override TOML
        ec2 = EC2(
            'test',
            config_file=StringIO(config_content),
            region=None,  # Should not override TOML
            access_key_id="AKIATEST"  # Should be added
        )
        
        assert ec2.config['region'] == 'us-west-2'  # TOML preserved
        assert ec2.config['profile'] == 'default'  # TOML preserved  
        assert ec2.config['access_key_id'] == 'AKIATEST'  # Constructor added

    @patch('pycloudlib.ec2.util._get_session')
    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_ec2_config_no_toml_with_required_values(self, mock_ssh_keys, mock_get_session):
        """Test EC2 with no TOML file but all required values provided."""
        # Mock AWS session
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session.resource.return_value = MagicMock()
        mock_session.region_name = "us-east-1"
        mock_get_session.return_value = mock_session
        
        # Mock SSH keys
        mock_ssh_keys.return_value = MagicMock()
        
        # No config file provided, but required values given
        ec2 = EC2(
            'test',
            region="us-east-1",
            access_key_id="AKIATEST",
            secret_access_key="SECRET"
        )
        
        # Should work with just constructor parameters
        assert ec2.config['region'] == 'us-east-1'
        assert ec2.config['access_key_id'] == 'AKIATEST'
        assert ec2.config['secret_access_key'] == 'SECRET'

    @patch('pycloudlib.config.parse_config')
    @patch('pycloudlib.ec2.util._get_session')
    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_ec2_config_validation_called(self, mock_ssh_keys, mock_get_session, mock_parse_config):
        """Test that configuration validation is called for EC2."""
        # Mock AWS session
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session.resource.return_value = MagicMock()
        mock_session.region_name = "us-west-2"
        mock_get_session.return_value = mock_session
        
        # Mock SSH keys
        mock_ssh_keys.return_value = MagicMock()
        
        # Mock parse_config to return a valid config
        mock_parse_config.return_value = {
            'ec2': {'region': 'us-west-2', 'profile': 'default'}
        }
        
        ec2 = EC2('test', region="us-west-2")
        
        # Verify parse_config was called with validation enabled
        mock_parse_config.assert_called_once()
        call_args = mock_parse_config.call_args
        assert call_args[1]['validate'] is True
        assert call_args[1]['cloud_type'] == 'ec2'