"""Test the enhanced configuration system."""

import pytest
from io import StringIO
from unittest.mock import patch

from pycloudlib.config import merge_configs, parse_config, validate_cloud_config


class TestConfigValidation:
    """Test configuration validation functionality."""

    def test_validate_ec2_config_valid(self):
        """Test that valid EC2 config passes validation."""
        config = {
            "region": "us-west-2",
            "profile": "default"
        }
        # Should not raise an exception
        validate_cloud_config("ec2", config)

    def test_validate_ec2_config_invalid_additional_property(self):
        """Test that EC2 config with invalid property fails validation."""
        config = {
            "region": "us-west-2", 
            "invalid_field": "should_fail"
        }
        with pytest.raises(ValueError, match="Additional properties are not allowed"):
            validate_cloud_config("ec2", config)

    def test_validate_azure_config_missing_required(self):
        """Test that Azure config missing required fields fails validation."""
        config = {
            "client_id": "test",
            # missing required fields: client_secret, subscription_id, tenant_id
        }
        with pytest.raises(ValueError, match="Invalid configuration for azure"):
            validate_cloud_config("azure", config)

    def test_validate_azure_config_valid(self):
        """Test that complete Azure config passes validation."""
        config = {
            "client_id": "test_client",
            "client_secret": "test_secret", 
            "subscription_id": "test_sub",
            "tenant_id": "test_tenant"
        }
        # Should not raise an exception
        validate_cloud_config("azure", config)

    def test_validate_unknown_cloud_type(self):
        """Test that unknown cloud type logs warning but doesn't fail."""
        config = {"some_field": "some_value"}
        # Should not raise an exception, just log warning
        validate_cloud_config("unknown_cloud", config)


class TestConfigMerging:
    """Test configuration merging functionality."""

    def test_merge_configs_basic(self):
        """Test basic config merging."""
        base = {"region": "us-west-2", "profile": "default"}
        override = {"region": "us-east-1"}
        
        result = merge_configs(base, override)
        
        assert result["region"] == "us-east-1"  # Override wins
        assert result["profile"] == "default"  # Base preserved

    def test_merge_configs_none_values_ignored(self):
        """Test that None values in override are ignored."""
        base = {"region": "us-west-2", "profile": "default"}
        override = {"region": None, "access_key_id": "AKIATEST"}
        
        result = merge_configs(base, override)
        
        assert result["region"] == "us-west-2"  # None ignored, base preserved
        assert result["profile"] == "default"  # Base preserved
        assert result["access_key_id"] == "AKIATEST"  # New value added

    def test_merge_configs_empty_override(self):
        """Test merging with empty override."""
        base = {"region": "us-west-2", "profile": "default"}
        override = {}
        
        result = merge_configs(base, override)
        
        assert result == base

    def test_merge_configs_empty_base(self):
        """Test merging with empty base."""
        base = {}
        override = {"region": "us-east-1", "access_key_id": "AKIATEST"}
        
        result = merge_configs(base, override)
        
        assert result == override


class TestParseConfigEnhanced:
    """Test enhanced parse_config functionality."""

    def test_parse_config_with_validation_success(self):
        """Test parsing config with successful validation."""
        config_content = """
[ec2]
region = "us-west-2"
profile = "default"
"""
        config = parse_config(
            StringIO(config_content), 
            validate=True, 
            cloud_type="ec2"
        )
        
        assert config["ec2"]["region"] == "us-west-2"
        assert config["ec2"]["profile"] == "default"

    def test_parse_config_with_validation_failure(self):
        """Test parsing config with validation failure."""
        config_content = """
[ec2]
region = "us-west-2"
invalid_field = "should_fail"
"""
        with pytest.raises(ValueError, match="Configuration validation failed"):
            parse_config(
                StringIO(config_content),
                validate=True,
                cloud_type="ec2"
            )

    def test_parse_config_validation_disabled(self):
        """Test parsing config with validation disabled."""
        config_content = """
[ec2]
region = "us-west-2"
invalid_field = "should_pass"
"""
        config = parse_config(
            StringIO(config_content),
            validate=False,
            cloud_type="ec2"
        )
        
        assert config["ec2"]["region"] == "us-west-2"
        assert config["ec2"]["invalid_field"] == "should_pass"

    def test_parse_config_no_cloud_type_validation(self):
        """Test parsing config without cloud_type specified (no validation)."""
        config_content = """
[ec2]
region = "us-west-2"
invalid_field = "should_pass"
"""
        config = parse_config(
            StringIO(config_content),
            validate=True,
            cloud_type=None
        )
        
        assert config["ec2"]["region"] == "us-west-2"
        assert config["ec2"]["invalid_field"] == "should_pass"

    def test_parse_config_cloud_section_missing(self):
        """Test parsing config when specified cloud section is missing."""
        config_content = """
[azure]
client_id = "test"
"""
        config = parse_config(
            StringIO(config_content),
            validate=True,
            cloud_type="ec2"  # ec2 section missing
        )
        
        # Should still parse successfully, just no validation occurs
        assert "azure" in config
        assert "ec2" not in config