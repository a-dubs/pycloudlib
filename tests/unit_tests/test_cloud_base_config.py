"""Test the configuration system integration with cloud classes."""

import pytest
from io import StringIO
from unittest.mock import patch, MagicMock

from pycloudlib.cloud import BaseCloud


class TestCloudClass(BaseCloud):
    """Test cloud implementation for testing configuration."""
    
    _type = "test"
    
    def __init__(self, tag, **kwargs):
        super().__init__(tag, **kwargs)
        
    def delete_image(self, image_id, **kwargs):
        pass
        
    def released_image(self, release, **kwargs):
        pass
        
    def daily_image(self, release, **kwargs):
        pass
        
    def image_serial(self, image_id):
        pass
        
    def get_instance(self, instance_id, *, username=None, **kwargs):
        pass
        
    def launch(self, image_id, instance_type=None, user_data=None, **kwargs):
        pass
        
    def snapshot(self, instance, clean=True, **kwargs):
        pass


class TestCloudBaseConfigurationSystem:
    """Test the base cloud configuration system."""
    
    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_config_toml_only(self, mock_ssh_keys):
        """Test cloud initialization with TOML config only."""
        mock_ssh_keys.return_value = MagicMock()
        
        config_content = '''
[test]
region = "us-west-2"
profile = "default"
public_key_path = "/fake/path"
'''
        
        cloud = TestCloudClass('test', config_file=StringIO(config_content))
        
        assert cloud.config['region'] == 'us-west-2'
        assert cloud.config['profile'] == 'default'
        assert cloud.config['public_key_path'] == '/fake/path'

    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_config_constructor_override(self, mock_ssh_keys):
        """Test cloud initialization with constructor parameters overriding TOML."""
        mock_ssh_keys.return_value = MagicMock()
        
        config_content = '''
[test]
region = "us-west-2"
profile = "default"
public_key_path = "/fake/path"
'''
        
        cloud = TestCloudClass(
            'test', 
            config_file=StringIO(config_content),
            region="us-east-1",  # Override TOML region
            access_key_id="AKIATEST"  # New parameter not in TOML
        )
        
        # Verify merging worked correctly
        assert cloud.config['region'] == 'us-east-1'  # Overridden
        assert cloud.config['profile'] == 'default'  # From TOML
        assert cloud.config['public_key_path'] == '/fake/path'  # From TOML
        assert cloud.config['access_key_id'] == 'AKIATEST'  # From constructor

    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_config_constructor_none_values_ignored(self, mock_ssh_keys):
        """Test that None values in constructor don't override TOML."""
        mock_ssh_keys.return_value = MagicMock()
        
        config_content = '''
[test]
region = "us-west-2"
profile = "default"
'''
        
        cloud = TestCloudClass(
            'test',
            config_file=StringIO(config_content),
            region=None,  # Should not override TOML
            access_key_id="AKIATEST"  # Should be added
        )
        
        assert cloud.config['region'] == 'us-west-2'  # TOML preserved
        assert cloud.config['profile'] == 'default'  # TOML preserved  
        assert cloud.config['access_key_id'] == 'AKIATEST'  # Constructor added

    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_config_no_toml_with_parameters(self, mock_ssh_keys):
        """Test cloud with no TOML file but constructor parameters."""
        mock_ssh_keys.return_value = MagicMock()
        
        cloud = TestCloudClass(
            'test',
            region="us-east-1",
            access_key_id="AKIATEST",
            secret_access_key="SECRET"
        )
        
        # Should work with just constructor parameters
        assert cloud.config['region'] == 'us-east-1'
        assert cloud.config['access_key_id'] == 'AKIATEST'
        assert cloud.config['secret_access_key'] == 'SECRET'

    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_config_validation_called(self, mock_ssh_keys):
        """Test that configuration validation is called when config file exists."""
        mock_ssh_keys.return_value = MagicMock()
        
        config_content = '''
[test]
region = "us-west-2"
profile = "default"
'''
        
        # This should parse and validate the config file
        with patch('pycloudlib.config.validate_cloud_config') as mock_validate:
            cloud = TestCloudClass('test', config_file=StringIO(config_content))
            
            # Verify validation was called
            mock_validate.assert_called_once_with('test', {'region': 'us-west-2', 'profile': 'default'})

    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_config_ssh_key_parameters_work(self, mock_ssh_keys):
        """Test that SSH key parameters can be passed via constructor."""
        mock_ssh_keys.return_value = MagicMock()
        
        config_content = '''
[test]
region = "us-west-2"
'''
        
        cloud = TestCloudClass(
            'test',
            config_file=StringIO(config_content),
            public_key_path="/custom/key.pub",
            private_key_path="/custom/key",
            key_name="custom-key"
        )
        
        # SSH key parameters should be in config
        assert cloud.config['public_key_path'] == '/custom/key.pub'
        assert cloud.config['private_key_path'] == '/custom/key'
        assert cloud.config['key_name'] == 'custom-key'
        
        # SSH key getter should be called with merged config values
        mock_ssh_keys.assert_called_once_with(
            public_key_path="/custom/key.pub",
            private_key_path="/custom/key", 
            name="custom-key"
        )