# This file is part of pycloudlib. See LICENSE file for license information.
"""Base class for all other clouds to provide consistent set of functions."""

import dataclasses
import enum
import getpass
import io
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Sequence

import paramiko

from pycloudlib.config import ConfigFile, parse_config
from pycloudlib.errors import CleanupError, InvalidTagNameError
from pycloudlib.instance import BaseInstance
from pycloudlib.key import KeyPair
from pycloudlib.util import (
    get_timestamped_tag,
    log_exception_list,
)

_RequiredValues = Optional[Sequence[Optional[Any]]]


@dataclasses.dataclass
class ImageInfo:
    """Basic information about an image."""

    id: str
    name: str


@enum.unique
class ImageType(enum.Enum):
    """Allowed image types when launching cloud images."""

    GENERIC = "generic"
    MINIMAL = "minimal"
    PRO = "Pro"
    PRO_FIPS = "Pro FIPS"


class BaseCloud(ABC):
    """Base Cloud Class."""

    _type = "base"

    def __init__(
        self,
        tag: str,
        timestamp_suffix: bool = True,
        config_file: Optional[ConfigFile] = None,
        required_values: Optional[_RequiredValues] = None,
    ):
        """Initialize base cloud class.

        Args:
            tag: string used to name and tag resources with
            timestamp_suffix: Append a timestamped suffix to the tag string.
            config_file: path to pycloudlib configuration file
        """
        self.created_instances: List[BaseInstance] = []
        self.created_images: List[str] = []

        self._log = logging.getLogger(
            "{}.{}".format(__name__, self.__class__.__name__)
        )
        self._check_and_set_config(config_file, required_values)

        user = getpass.getuser()
        self.key_pair = KeyPair(
            public_key_path=os.path.expandvars(
                self.config.get("public_key_path", f"~{user}/.ssh/id_rsa.pub")
            ),
            private_key_path=os.path.expandvars(
                self.config.get("private_key_path", "")
            ),
            name=self.config.get("key_name", user),
        )

        self.tag = get_timestamped_tag(tag) if timestamp_suffix else tag
        self._validate_tag(self.tag)

    def __enter__(self):
        """Enter context manager for this class."""
        return self

    def __exit__(self, _type, _value, _trackback):
        """Cleanup context manager for this class."""
        exceptions = self.clean()
        log_exception_list(exceptions)
        if exceptions:
            raise CleanupError(exceptions)

    @abstractmethod
    def delete_image(self, image_id: str, **kwargs):
        """Delete an image.

        Args:
            image_id: string, id of the image to delete
            **kwargs: dictionary of other arguments to pass to delete_image
        """
        raise NotImplementedError

    @abstractmethod
    def released_image(self, release, **kwargs):
        """ID of the latest released image for a particular release.

        Args:
            release: The release to look for

        Returns:
            A single string with the latest released image ID for the
            specified release.

        """
        raise NotImplementedError

    @abstractmethod
    def daily_image(self, release: str, **kwargs):
        """ID of the latest daily image for a particular release.

        Args:
            release: The release to look for

        Returns:
            A single string with the latest daily image ID for the
            specified release.

        """
        raise NotImplementedError

    @abstractmethod
    def image_serial(self, image_id):
        """Find the image serial of the latest daily image for a particular release.

        Args:
            image_id: string, Ubuntu image id

        Returns:
            string, serial of latest image

        """
        raise NotImplementedError

    def get_image_id_from_name(self, name: str) -> str:
        """
        Get the id of the first image whose name contains the given name.

        The name does not need to be an exact match, just a substring of
        the image name.

        Args:
            name: string, name of the image to search for

        Returns:
            string, image ID
        """
        raise NotImplementedError

    @abstractmethod
    def get_instance(
        self, instance_id, *, username: Optional[str] = None, **kwargs
    ) -> BaseInstance:
        """Get an instance by id.

        Args:
            instance_id: ID identifying the instance
            username: username to use when connecting via SSH

        Returns:
            An instance object to use to manipulate the instance further.

        """
        raise NotImplementedError

    @abstractmethod
    def launch(
        self,
        image_id: str,
        instance_type=None,
        user_data=None,
        **kwargs,
    ) -> BaseInstance:
        """Launch an instance.

        Args:
            image_id: string, image ID to use for the instance
            instance_type: string, type of instance to create
            user_data: used by cloud-init to run custom scripts/configuration
            username: username to use when connecting via SSH
            **kwargs: dictionary of other arguments to pass to launch

        Returns:
            An instance object to use to manipulate the instance further.

        """
        raise NotImplementedError

    @abstractmethod
    def snapshot(self, instance, clean=True, **kwargs):
        """Snapshot an instance and generate an image from it.

        Args:
            instance: Instance to snapshot
            clean: run instance clean method before taking snapshot

        Returns:
            An image id

        """
        raise NotImplementedError

    # pylint: disable=broad-except
    def clean(self) -> List[Exception]:
        """Cleanup ALL artifacts associated with this Cloud instance.

        This includes all instances, snapshots, resources, etc.
        To ensure cleanup isn't interrupted, any exceptions raised during
        cleanup operations will be collected and returned.
        """
        exceptions: List[Exception] = []
        for instance in self.created_instances:
            try:
                instance.delete()
            except Exception as e:
                exceptions.append(e)
        for image_id in self.created_images:
            try:
                self.delete_image(image_id)
            except Exception as e:
                exceptions.append(e)
        return exceptions

    def list_keys(self):
        """List ssh key names present on the cloud for accessing instances.

        Returns:
           A list of strings of key pair names accessible to the cloud.

        """
        raise NotImplementedError

    def create_key_pair(self):
        """Create and set a ssh key pair for a cloud instance.

        Returns:
            A tuple containing the public and private key created
        """
        key = paramiko.RSAKey.generate(4096)
        priv_str = io.StringIO()

        pub_key = "{} {}".format(key.get_name(), key.get_base64())
        key.write_private_key(priv_str, password=None)

        return pub_key, priv_str.getvalue()

    def use_key(self, public_key_path, private_key_path=None, name=None):
        """Use an existing key.

        Args:
            public_key_path: path to the public key to upload
            private_key_path: path to the private key
            name: name to reference key by
        """
        self._log.debug("using SSH key from %s", public_key_path)
        self.key_pair = KeyPair(public_key_path, private_key_path, name)

    def _check_and_set_config(
        self,
        config_file: Optional[ConfigFile],
        required_values: _RequiredValues,
    ):
        """Set pycloudlib configuration.

        Checks if values required to launch a cloud instance are present.
        Values should be present in pycloudlib config file or passed to the
        cloud's constructor directly.

        Args:
            config_file: path to pycloudlib configuration file
            required_values: a list containing all the required values for
                the cloud that were passed to the cloud's constructor
        """
        # if all required values were passed to the cloud's constructor,
        # there is no need to parse the config file. If some (but not all)
        # of them were provided, config file is loaded and the values that
        # were passed in work as overrides
        if required_values and all(v is not None for v in required_values):
            self.config = {}
        else:
            self.config = parse_config(config_file)[self._type]

    @staticmethod
    def _validate_tag(tag: str):
        """
        Ensure that this tag is a valid name for cloud resources.

        Rules:
        - All letters must be lowercase
        - Must be between 1 and 63 characters long
        - Must not start or end with a hyphen
        - Must be alphanumeric and hyphens only

        :param tag: tag to validate

        :raises InvalidTagNameError: if the tag is invalid
        """
        rules_failed = []
        # all letters must be lowercase
        if any(c.isupper() for c in tag):
            rules_failed.append("All letters must be lowercase")
        # must be between 1 and 63 characters long
        if len(tag) < 1 or len(tag) > 63:
            rules_failed.append("Must be between 1 and 63 characters long")
        # must not start or end with a hyphen
        if tag and (tag[0] in ("-") or tag[-1] in ("-")):
            rules_failed.append("Must not start or end with a hyphen")
        # must be alphanumeric and hyphens only
        if not re.match(r"^[a-z0-9-]*$", tag):
            rules_failed.append("Must be alphanumeric and hyphens only")

        if rules_failed:
            raise InvalidTagNameError(tag=tag, rules_failed=rules_failed)

    # def upload_and_register_image(
    #     self,
    #     path_to_local_image: str,
    #     image_name: str,
    #     storage_container_name: str,
    # ) -> ImageInfo:
    #     """
    #     Uploads given image binary to the cloud and registers it as an image.

    #     Args:
    #         path_to_local_image: The local file path of the image to upload.
    #         image_name: The name to upload the image as and to register.
    #         storage_container_name: The name of the storage container/bucket
    #             where the file should be uploaded.
    #     """
    #     raise NotImplementedError

    #

    # def create_image_from_local_file(
    #     self,
    #     path_to_local_image_file: str,
    #     image_name: str,
    #     storage_container_name: str,
    # ) -> ImageInfo:
    #     """
    #     Uploads an image file to a Google Cloud Storage bucket and registers it as a custom image in GCE.

    #     Args:
    #         path_to_local_image_file: The local file path of the image to upload.
    #         image_name: The name to upload the image as and to register.
    #         storage_container_name: The name of the storage container/bucket
    #             where the file should be uploaded.
    #     """
    #     # Upload the image to GCS
    #     # create destination file name using image name + image file extension
    #     destination_file_name = f"{image_name}.tar.gz"
    #     print(f"Uploading image '{image_name}' to {storage_container_name} at {destination_file_name}")
    #     gcs_image_path = self.upload_image_to_gcs(
    #         storage_container_name, path_to_local_image, destination_file_name
    #     )
    #     print(f"Image '{image_name}' uploaded successfully to GCS.")
    #     print(f"Registering custom image in GCE from {gcs_image_path}")
    #     # Register the custom image from GCS
    #     return self.register_custom_image(image_name, gcs_image_path)

    # optional - raise NotImplementedError from base class
    def upload_local_file_to_cloud_storage(
        self,
        storage_name,
        path_to_local_image,
        destination_file_name,
    ):
        """
        Uploads a file to a storage destination on the Cloud.
        Args:
            storage_name: The name of the storage destination on the Cloud to upload the file to.
            path_to_local_image: The local file path of the image to upload.
            destination_file_name: The name of the file in the storage destination.

        Returns:
            str: ???
        """
        raise NotImplementedError

    # public api function on clouds
    @abstractmethod
    def create_image_from_local_file(
        self,
        local_file_path: str,
        image_name: str,
        intermediary_storage_name: str,
    ):
        """
        Uploads local image file to intermediary storage on the Cloud and creates a custom image from it.

        Args:
            local_file_path: The local file path of the image to upload.
            image_name: The name to upload the image as and to register.
            intermediary_storage_name: The intermediary storage destination on the Cloud to upload the file to before creating the image.
        """
        raise NotImplementedError

    # optional per cloud as necessary to do "registering" of images
    # optional - raise NotImplementedError from base class
    def _create_image_from_cloud_storage(
        self,
        storage_name,
        image_name,
        image_family=None,
        image_description=None,
    ) -> ImageInfo:
        """
        Registers a custom image in GCE from an image stored in a Google Cloud Storage bucket.

        Args:
            storage_name: The name of the storage destination on the Cloud to upload the file to.
            image_name: The name the image will be created with.
            image_family: The family name of the image.
            image_description: A description of the image.
        """
        raise NotImplementedError
