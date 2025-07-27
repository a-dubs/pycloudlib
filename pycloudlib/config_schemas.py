"""Configuration schemas for TOML validation."""

from typing import Any, Dict

# Base schema with common fields for all cloud types
BASE_CLOUD_SCHEMA = {
    "type": "object",
    "properties": {
        "public_key_path": {
            "type": "string",
            "description": "Path to SSH public key file"
        },
        "private_key_path": {
            "type": "string", 
            "description": "Path to SSH private key file"
        },
        "key_name": {
            "type": "string",
            "description": "Name for the SSH key pair"
        }
    },
    "additionalProperties": False
}

# EC2-specific configuration schema
EC2_SCHEMA = {
    "type": "object",
    "properties": {
        **BASE_CLOUD_SCHEMA["properties"],
        "region": {
            "type": "string",
            "description": "AWS region"
        },
        "access_key_id": {
            "type": "string", 
            "description": "AWS access key ID"
        },
        "secret_access_key": {
            "type": "string",
            "description": "AWS secret access key"
        },
        "profile": {
            "type": "string",
            "description": "AWS profile name from ~/.aws/config"
        }
    },
    "additionalProperties": False
}

# Azure-specific configuration schema
AZURE_SCHEMA = {
    "type": "object", 
    "properties": {
        **BASE_CLOUD_SCHEMA["properties"],
        "client_id": {
            "type": "string",
            "description": "Azure client ID"
        },
        "client_secret": {
            "type": "string",
            "description": "Azure client secret"  
        },
        "subscription_id": {
            "type": "string",
            "description": "Azure subscription ID"
        },
        "tenant_id": {
            "type": "string",
            "description": "Azure tenant ID"
        },
        "region": {
            "type": "string",
            "description": "Azure region",
            "default": "centralus"
        }
    },
    "required": ["client_id", "client_secret", "subscription_id", "tenant_id"],
    "additionalProperties": False
}

# GCE-specific configuration schema  
GCE_SCHEMA = {
    "type": "object",
    "properties": {
        **BASE_CLOUD_SCHEMA["properties"],
        "credentials_path": {
            "type": "string",
            "description": "Path to GCE credentials JSON file"
        },
        "project": {
            "type": "string", 
            "description": "GCE project ID"
        },
        "region": {
            "type": "string",
            "description": "GCE region",
            "default": "us-west2"
        },
        "zone": {
            "type": "string",
            "description": "GCE zone",
            "default": "a"
        },
        "service_account_email": {
            "type": "string",
            "description": "Service account email"
        }
    },
    "required": ["credentials_path", "project"],
    "additionalProperties": False
}

# IBM-specific configuration schema
IBM_SCHEMA = {
    "type": "object",
    "properties": {
        **BASE_CLOUD_SCHEMA["properties"],
        "resource_group": {
            "type": "string",
            "description": "IBM resource group",
            "default": "Default"
        },
        "vpc": {
            "type": "string",
            "description": "VPC name"
        },
        "api_key": {
            "type": "string",
            "description": "IBM Cloud API key"
        },
        "region": {
            "type": "string",
            "description": "IBM region",
            "default": "eu-de"
        },
        "zone": {
            "type": "string", 
            "description": "IBM zone",
            "default": "eu-de-2"
        },
        "floating_ip_substring": {
            "type": "string",
            "description": "String to search for in floating IP"
        }
    },
    "additionalProperties": False
}

# IBM Classic-specific configuration schema
IBM_CLASSIC_SCHEMA = {
    "type": "object",
    "properties": {
        **BASE_CLOUD_SCHEMA["properties"],
        "username": {
            "type": "string",
            "description": "IBM Classic username"
        },
        "api_key": {
            "type": "string", 
            "description": "IBM Classic API key"
        },
        "domain_name": {
            "type": "string",
            "description": "Domain name"
        }
    },
    "required": ["username", "api_key", "domain_name"],
    "additionalProperties": False
}

# LXD configuration schema (minimal)
LXD_SCHEMA = {
    "type": "object",
    "properties": {
        **BASE_CLOUD_SCHEMA["properties"]
    },
    "additionalProperties": False
}

# OCI-specific configuration schema
OCI_SCHEMA = {
    "type": "object",
    "properties": {
        **BASE_CLOUD_SCHEMA["properties"],
        "config_path": {
            "type": "string",
            "description": "Path to OCI config file",
            "default": "~/.oci/config"
        },
        "availability_domain": {
            "type": "string",
            "description": "OCI availability domain"
        },
        "compartment_id": {
            "type": "string",
            "description": "OCI compartment ID"
        },
        "region": {
            "type": "string",
            "description": "OCI region",
            "default": "us-phoenix-1"
        },
        "profile": {
            "type": "string",
            "description": "OCI profile name",
            "default": "DEFAULT"
        },
        "vcn_name": {
            "type": "string",
            "description": "VCN name"
        }
    },
    "required": ["config_path", "availability_domain", "compartment_id"],
    "additionalProperties": False
}

# OpenStack-specific configuration schema
OPENSTACK_SCHEMA = {
    "type": "object",
    "properties": {
        **BASE_CLOUD_SCHEMA["properties"],
        "network": {
            "type": "string",
            "description": "OpenStack network name"
        }
    },
    "required": ["network"],
    "additionalProperties": False
}

# QEMU-specific configuration schema
QEMU_SCHEMA = {
    "type": "object",
    "properties": {
        **BASE_CLOUD_SCHEMA["properties"],
        "image_dir": {
            "type": "string",
            "description": "Path to image directory"
        },
        "working_dir": {
            "type": "string",
            "description": "Working directory",
            "default": "/tmp"
        },
        "qemu_binary": {
            "type": "string",
            "description": "QEMU binary path",
            "default": "qemu-system-x86_64"
        }
    },
    "required": ["image_dir"],
    "additionalProperties": False
}

# VMware-specific configuration schema
VMWARE_SCHEMA = {
    "type": "object",
    "properties": {
        **BASE_CLOUD_SCHEMA["properties"],
        "server": {
            "type": "string",
            "description": "VMware server URL"
        },
        "username": {
            "type": "string",
            "description": "VMware username"
        },
        "password": {
            "type": "string",
            "description": "VMware password"
        },
        "datacenter": {
            "type": "string",
            "description": "VMware datacenter"
        },
        "datastore": {
            "type": "string",
            "description": "VMware datastore"
        },
        "folder": {
            "type": "string",
            "description": "VMware folder"
        },
        "insecure_transport": {
            "type": "boolean",
            "description": "Allow insecure transport",
            "default": False
        }
    },
    "required": ["server", "username", "password", "datacenter", "datastore", "folder"],
    "additionalProperties": False
}

# Mapping of cloud types to their schemas
CLOUD_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "ec2": EC2_SCHEMA,
    "azure": AZURE_SCHEMA,
    "gce": GCE_SCHEMA,
    "ibm": IBM_SCHEMA,
    "ibm_classic": IBM_CLASSIC_SCHEMA,
    "lxd": LXD_SCHEMA,
    "oci": OCI_SCHEMA,
    "openstack": OPENSTACK_SCHEMA,
    "qemu": QEMU_SCHEMA,
    "vmware": VMWARE_SCHEMA
}