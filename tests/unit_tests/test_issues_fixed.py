"""Test to verify that issues #466 and #457 are fixed."""

import pytest
from io import StringIO
from unittest.mock import patch, MagicMock

from pycloudlib.cloud import BaseCloud


class MockEC2Cloud(BaseCloud):
    """Mock EC2 cloud implementation for testing validation."""
    
    _type = "ec2"
    
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


class MockCloud(BaseCloud):
    """Mock cloud implementation for testing."""
    
    _type = "test"
    
    def __init__(self, tag, **kwargs):
        # Extract parameters that would be "required values" for this cloud
        required_params = [
            kwargs.get('region'),
            kwargs.get('access_key_id'),
            kwargs.get('secret_access_key')
        ]
        super().__init__(tag, required_values=required_params, **kwargs)
        
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


class TestIssue466Fix:
    """Test that issue #466 is fixed: TOML is always parsed and can be overridden."""

    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_required_values_provided_still_parses_toml(self, mock_ssh_keys):
        """Test that providing all required values still parses TOML file.
        
        This is the core issue #466: previously, if all required values were
        provided, the TOML file was completely ignored.
        """
        mock_ssh_keys.return_value = MagicMock()
        
        # TOML config with additional settings
        config_content = '''
[test]
region = "us-west-2"
access_key_id = "AKIATOML"
secret_access_key = "TOMLSECRET"
profile = "toml-profile"
public_key_path = "/toml/key.pub"
custom_setting = "from_toml"
'''
        
        # Provide all "required values" - previously this would ignore TOML
        cloud = MockCloud(
            'test',
            config_file=StringIO(config_content),
            region="us-east-1",  # Override TOML
            access_key_id="AKIARUNTIME",  # Override TOML
            secret_access_key="RUNTIMESECRET"  # Override TOML
        )
        
        # Verify that TOML was parsed AND constructor overrides work
        assert cloud.config['region'] == 'us-east-1'  # Constructor override
        assert cloud.config['access_key_id'] == 'AKIARUNTIME'  # Constructor override
        assert cloud.config['secret_access_key'] == 'RUNTIMESECRET'  # Constructor override
        assert cloud.config['profile'] == 'toml-profile'  # From TOML (not overridden)
        assert cloud.config['public_key_path'] == '/toml/key.pub'  # From TOML
        assert cloud.config['custom_setting'] == 'from_toml'  # From TOML

    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_toml_as_base_config_with_runtime_overrides(self, mock_ssh_keys):
        """Test that TOML acts as base config with runtime overrides."""
        mock_ssh_keys.return_value = MagicMock()
        
        config_content = '''
[test]
region = "us-west-2"
access_key_id = "AKIATOML"
secret_access_key = "TOMLSECRET"
instance_type = "t3.micro"
vpc_id = "vpc-toml123"
security_group = "sg-toml456"
'''
        
        # Only override some values, others should come from TOML
        cloud = MockCloud(
            'test',
            config_file=StringIO(config_content),
            region="us-east-1",  # Override
            instance_type="t3.large"  # Override
            # access_key_id, secret_access_key should come from TOML
            # vpc_id, security_group should come from TOML
        )
        
        # Verify proper merging
        assert cloud.config['region'] == 'us-east-1'  # Overridden
        assert cloud.config['instance_type'] == 't3.large'  # Overridden
        assert cloud.config['access_key_id'] == 'AKIATOML'  # From TOML
        assert cloud.config['secret_access_key'] == 'TOMLSECRET'  # From TOML
        assert cloud.config['vpc_id'] == 'vpc-toml123'  # From TOML
        assert cloud.config['security_group'] == 'sg-toml456'  # From TOML


class TestIssue457Features:
    """Test that issue #457 features are implemented: align TOML and constructor options."""

    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_ssh_keys_can_be_passed_at_runtime(self, mock_ssh_keys):
        """Test that SSH keys can now be passed at runtime, not just in TOML.
        
        This addresses the SSH key issue mentioned in #457.
        """
        mock_ssh_keys.return_value = MagicMock()
        
        config_content = '''
[test]
region = "us-west-2"
access_key_id = "AKIATOML"
secret_access_key = "TOMLSECRET"
'''
        
        # Pass SSH key settings at runtime
        cloud = MockCloud(
            'test',
            config_file=StringIO(config_content),
            public_key_path="/runtime/key.pub",
            private_key_path="/runtime/key",
            key_name="runtime-key"
        )
        
        # Verify SSH keys are in config and _get_ssh_keys was called correctly
        assert cloud.config['public_key_path'] == '/runtime/key.pub'
        assert cloud.config['private_key_path'] == '/runtime/key'
        assert cloud.config['key_name'] == 'runtime-key'
        
        mock_ssh_keys.assert_called_once_with(
            public_key_path="/runtime/key.pub",
            private_key_path="/runtime/key",
            name="runtime-key"
        )

    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_any_toml_setting_can_be_constructor_parameter(self, mock_ssh_keys):
        """Test that any setting available in TOML can be passed to constructor."""
        mock_ssh_keys.return_value = MagicMock()
        
        # Test with no TOML file, all parameters via constructor
        cloud = MockCloud(
            'test',
            region="us-west-2",
            access_key_id="AKIATEST",
            secret_access_key="TESTSECRET",
            profile="test-profile",
            public_key_path="/test/key.pub",
            private_key_path="/test/key",
            key_name="test-key",
            vpc_id="vpc-123456",
            security_group="sg-789012",
            instance_type="t3.medium",
            custom_setting="runtime_value"
        )
        
        # All settings should be available in config
        assert cloud.config['region'] == 'us-west-2'
        assert cloud.config['access_key_id'] == 'AKIATEST'
        assert cloud.config['secret_access_key'] == 'TESTSECRET'
        assert cloud.config['profile'] == 'test-profile'
        assert cloud.config['public_key_path'] == '/test/key.pub'
        assert cloud.config['private_key_path'] == '/test/key'
        assert cloud.config['key_name'] == 'test-key'
        assert cloud.config['vpc_id'] == 'vpc-123456'
        assert cloud.config['security_group'] == 'sg-789012'
        assert cloud.config['instance_type'] == 't3.medium'
        assert cloud.config['custom_setting'] == 'runtime_value'


class TestConfigValidation:
    """Test TOML validation features."""

    @patch('pycloudlib.cloud.BaseCloud._get_ssh_keys')
    def test_invalid_toml_caught_immediately(self, mock_ssh_keys):
        """Test that TOML validation catches configuration errors immediately."""
        mock_ssh_keys.return_value = MagicMock()
        
        # Invalid EC2 config (has extra invalid field that's not in the schema)
        config_content = '''
[ec2]
region = "us-west-2"
profile = "default"
invalid_field_not_in_schema = "this should fail validation"
'''
        
        # This should raise a validation error immediately
        with pytest.raises(ValueError, match="Configuration validation failed"):
            MockEC2Cloud('test', config_file=StringIO(config_content))