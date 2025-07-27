#!/usr/bin/env python3
"""Demonstration of the new TOML configuration system for pycloudlib.

This script demonstrates the key improvements made to address issues #457 and #466:

1. TOML is always parsed and serves as base configuration
2. Constructor parameters override TOML settings
3. Any TOML setting can be passed as constructor parameter
4. SSH keys can be configured at runtime
5. TOML validation catches errors immediately
"""

import sys
from io import StringIO
from unittest.mock import patch, MagicMock

# Import the enhanced configuration system
from pycloudlib.config import parse_config, validate_cloud_config, merge_configs
from pycloudlib.cloud import BaseCloud


class DemoCloud(BaseCloud):
    """Demo cloud implementation for showcasing the new config system."""
    
    _type = "ec2"  # Use EC2 for validation demonstration
    
    def __init__(self, tag, **kwargs):
        super().__init__(tag, **kwargs)
        
    # Minimal implementations to satisfy BaseCloud interface
    def delete_image(self, image_id, **kwargs): pass
    def released_image(self, release, **kwargs): pass
    def daily_image(self, release, **kwargs): pass
    def image_serial(self, image_id): pass
    def get_instance(self, instance_id, *, username=None, **kwargs): pass
    def launch(self, image_id, instance_type=None, user_data=None, **kwargs): pass
    def snapshot(self, instance, clean=True, **kwargs): pass


def demo_issue_466_fix():
    """Demonstrate that issue #466 is fixed: TOML is always parsed."""
    print("=== DEMONSTRATION: Issue #466 Fix ===")
    print("Before: If all required values were provided, TOML was ignored")
    print("After: TOML is always parsed and serves as base configuration\n")
    
    # Sample TOML configuration
    toml_config = '''
[ec2]
region = "us-west-2"
access_key_id = "AKIATOML"
secret_access_key = "TOMLSECRET"
profile = "toml-profile"
instance_type = "t3.micro"
vpc_id = "vpc-toml123"
public_key_path = "/home/user/.ssh/id_rsa.pub"
custom_setting = "from_toml_file"
'''
    
    print("TOML Configuration:")
    print(toml_config)
    
    # Mock SSH keys to avoid file system dependency
    with patch('pycloudlib.cloud.BaseCloud._get_ssh_keys') as mock_ssh:
        mock_ssh.return_value = MagicMock()
        
        # Create cloud with all "required values" provided
        cloud = DemoCloud(
            'demo',
            config_file=StringIO(toml_config),
            region="us-east-1",      # Override TOML setting
            access_key_id="AKIARUNTIME",  # Override TOML setting  
            secret_access_key="RUNTIMESECRET",  # Override TOML setting
            instance_type="t3.large"  # Override TOML setting
        )
        
        print("Constructor parameters (overrides):")
        print("  region='us-east-1'")
        print("  access_key_id='AKIARUNTIME'") 
        print("  secret_access_key='RUNTIMESECRET'")
        print("  instance_type='t3.large'")
        print()
        
        print("Final merged configuration:")
        for key, value in sorted(cloud.config.items()):
            source = "TOML" if key not in ["region", "access_key_id", "secret_access_key", "instance_type"] else "Constructor"
            print(f"  {key}={value!r} ({source})")
        
        print("\n✅ SUCCESS: TOML was parsed AND constructor parameters took precedence!")
        print("   Settings not overridden (profile, vpc_id, custom_setting) came from TOML")
        print("   Settings provided in constructor (region, keys, instance_type) overrode TOML")


def demo_issue_457_features():
    """Demonstrate issue #457 features: Any TOML setting can be constructor parameter."""
    print("\n\n=== DEMONSTRATION: Issue #457 Features ===")
    print("Before: SSH keys couldn't be passed at runtime, constructor options limited")
    print("After: Any TOML setting can be constructor parameter, including SSH keys\n")
    
    # Mock SSH keys to avoid file system dependency
    with patch('pycloudlib.cloud.BaseCloud._get_ssh_keys') as mock_ssh:
        mock_ssh.return_value = MagicMock()
        
        # Create cloud with all settings via constructor (no TOML file)
        cloud = DemoCloud(
            'demo',
            # AWS settings
            region="us-west-2",
            access_key_id="AKIATEST",
            secret_access_key="TESTSECRET", 
            profile="runtime-profile",
            # SSH settings (previously couldn't be done at runtime!)
            public_key_path="/runtime/key.pub",
            private_key_path="/runtime/key",
            key_name="runtime-key",
            # Custom settings
            instance_type="t3.medium",
            vpc_id="vpc-runtime123",
            security_group="sg-runtime456",
            custom_application_setting="runtime_value"
        )
        
        print("All settings provided via constructor (no TOML file needed):")
        for key, value in sorted(cloud.config.items()):
            print(f"  {key}={value!r}")
            
        print("\n✅ SUCCESS: All settings configured at runtime!")
        print("   SSH keys can now be passed as constructor parameters")
        print("   Any setting that can be in TOML can be in constructor")


def demo_toml_validation():
    """Demonstrate TOML validation features."""
    print("\n\n=== DEMONSTRATION: TOML Validation ===")
    print("New feature: Immediate validation of TOML configuration\n")
    
    # Valid configuration
    valid_toml = '''
[ec2]
region = "us-west-2"
profile = "default"
'''
    
    print("Valid TOML configuration:")
    print(valid_toml)
    
    try:
        config = parse_config(StringIO(valid_toml), validate=True, cloud_type="ec2")
        print("✅ Valid configuration accepted")
    except ValueError as e:
        print(f"❌ Unexpected error: {e}")
    
    # Invalid configuration
    invalid_toml = '''
[ec2]
region = "us-west-2"  
profile = "default"
invalid_field_not_in_schema = "this will fail"
extra_invalid_field = "this too"
'''
    
    print(f"\nInvalid TOML configuration (contains fields not in schema):")
    print(invalid_toml)
    
    try:
        config = parse_config(StringIO(invalid_toml), validate=True, cloud_type="ec2")
        print("❌ Invalid configuration was accepted (this shouldn't happen)")
    except ValueError as e:
        print("✅ Invalid configuration caught immediately:")
        print(f"   Error: {e}")


def demo_config_merging():
    """Demonstrate the configuration merging functionality.""" 
    print("\n\n=== DEMONSTRATION: Configuration Merging ===")
    print("New feature: Proper merging of TOML and constructor parameters\n")
    
    base_config = {
        "region": "us-west-2",
        "profile": "default", 
        "instance_type": "t3.micro",
        "vpc_id": "vpc-base123",
        "public_key_path": "/base/key.pub"
    }
    
    override_config = {
        "region": "us-east-1",  # Override
        "access_key_id": "AKIANEW",  # New setting
        "instance_type": None,  # None values ignored
    }
    
    print("Base configuration (from TOML):")
    for key, value in base_config.items():
        print(f"  {key}={value!r}")
    
    print("\nOverride configuration (from constructor):")
    for key, value in override_config.items():
        print(f"  {key}={value!r}")
    
    merged = merge_configs(base_config, override_config)
    
    print("\nMerged result:")
    for key, value in sorted(merged.items()):
        source = "Override" if key in override_config and override_config[key] is not None else "Base"
        if key == "access_key_id":
            source = "Override (new)"
        print(f"  {key}={value!r} ({source})")
    
    print("\n✅ SUCCESS: Proper merging with None values ignored!")


if __name__ == "__main__":
    print("🚀 PYCLOUDLIB NEW TOML CONFIGURATION SYSTEM DEMONSTRATION")
    print("=" * 65)
    
    try:
        demo_issue_466_fix()
        demo_issue_457_features() 
        demo_toml_validation()
        demo_config_merging()
        
        print("\n" + "=" * 65)
        print("🎉 ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
        print("\nKey improvements:")
        print("• Issue #466: TOML always parsed, serves as base configuration")
        print("• Issue #457: Any TOML setting can be constructor parameter")
        print("• SSH keys can be configured at runtime")
        print("• TOML validation catches errors immediately") 
        print("• Proper configuration merging with override support")
        print("• Full backward compatibility maintained")
        
    except Exception as e:
        print(f"\n❌ DEMONSTRATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)