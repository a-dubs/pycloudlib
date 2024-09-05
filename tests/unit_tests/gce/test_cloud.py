"""Tests related to pycloudlib.gce.cloud module."""

import mock
import pytest

from pycloudlib.cloud import ImageType
from pycloudlib.gce.cloud import GCE
from google.cloud import compute_v1
from google.cloud.compute_v1.services.images.pagers import ListPager

# mock module path
MPATH = "pycloudlib.gce.cloud."


class FakeGCE(GCE):
    """GCE Class that doesn't load config or make requests during __init__."""

    # pylint: disable=super-init-not-called
    def __init__(self, *_, **__):
        """Fake __init__ that sets mocks for needed variables."""
        self._log = mock.MagicMock()
        self._images_client = mock.MagicMock(spec=compute_v1.ImagesClient)


# pylint: disable=protected-access,missing-function-docstring
class TestGCE:
    """General GCE testing."""

    @pytest.mark.parametrize(
        [
            "release",
            "arch",
            "api_side_effects",
            "expected_filter_calls",
            "expected_image_list",
        ],
        [
            pytest.param(
                "xenial",
                "arm64",
                [Exception()],
                [],
                [],
                id="xenial_no_arm64_support_zero_sdk_list_calls",
            ),
            pytest.param(
                "xenial",
                "x86_64",
                [
                    ListPager(
                        method=mock.MagicMock(),
                        request=compute_v1.ListImagesRequest(
                            project="project-name",
                            filter="name=name-filter",
                            max_results=500,
                            page_token="",
                        ),
                        response=compute_v1.ImageList(
                            items=[
                                compute_v1.Image(name="image1"),
                                compute_v1.Image(name="image2"),
                                compute_v1.Image(name="image3"),
                            ]
                        ),
                    ),
                    Exception(),
                ],
                [
                    mock.call(
                        compute_v1.ListImagesRequest(
                            project="project-name",
                            filter="name=name-filter",
                            max_results=500,
                            page_token="",
                        )
                    )
                ],
                [
                    compute_v1.Image(name="image1"),
                    compute_v1.Image(name="image2"),
                    compute_v1.Image(name="image3"),
                ],
                id="xenial_x86_64_suppport_one_sdk_list_call_empty_pagetoken",
            ),
            pytest.param(
                "kinetic",
                "arm64",
                [
                    ListPager(
                        method=mock.MagicMock(),
                        request=compute_v1.ListImagesRequest(
                            project="project-name",
                            filter="(name=name-filter) AND (architecture=ARM64)",
                            max_results=500,
                            page_token="",
                        ),
                        response=compute_v1.ImageList(
                            items=[
                                compute_v1.Image(name="image1"),
                                compute_v1.Image(name="image2"),
                                compute_v1.Image(name="image3"),
                            ],
                            next_page_token="something",
                        ),
                    ),
                    ListPager(
                        method=mock.MagicMock(),
                        request=compute_v1.ListImagesRequest(
                            project="project-name",
                            filter="(name=name-filter) AND (architecture=ARM64)",
                            max_results=500,
                            page_token="something",
                        ),
                        response=compute_v1.ImageList(
                            items=[
                                compute_v1.Image(name="image4"),
                                compute_v1.Image(name="image5"),
                                compute_v1.Image(name="image6"),
                            ]
                        ),
                    ),
                    Exception(),
                ],
                [
                    mock.call(
                        compute_v1.ListImagesRequest(
                            project="project-name",
                            filter="(name=name-filter) AND (architecture=ARM64)",
                            max_results=500,
                            page_token="",
                        )
                    ),
                    mock.call(
                        compute_v1.ListImagesRequest(
                            project="project-name",
                            filter="(name=name-filter) AND (architecture=ARM64)",
                            max_results=500,
                            page_token="something",
                        )
                    ),
                ],
                [
                    compute_v1.Image(name="image1"),
                    compute_v1.Image(name="image2"),
                    compute_v1.Image(name="image3"),
                    compute_v1.Image(name="image4"),
                    compute_v1.Image(name="image5"),
                    compute_v1.Image(name="image6"),
                ],
                id="non_xenial_arm64_suppport_one_sdk_list_call_per_page",
            ),
        ],
    )
    def test_query_image_list(  # noqa: D102
        self,
        release,
        arch,
        api_side_effects,
        expected_filter_calls,
        expected_image_list,
    ):
        gce = FakeGCE(tag="tag")
        with mock.patch.object(gce, "_images_client") as m_images:
            m_images.list.side_effect = api_side_effects

            qil = gce._query_image_list(
                release, "project-name", "name-filter", arch
            )
            assert expected_image_list == qil
            assert m_images.list.call_args_list == expected_filter_calls

    @mock.patch(
        MPATH + "GCE._query_image_list",
        return_value=ListPager(
            method=mock.MagicMock(),
            request=compute_v1.ListImagesRequest(
                project="project-name",
                filter="name=name-filter",
                max_results=500,
                page_token="",
            ),
            response=compute_v1.ImageList(
                items=[
                    compute_v1.Image(id="2", name="2", creation_timestamp="2"),
                    compute_v1.Image(id="4", name="4", creation_timestamp="4"),
                    compute_v1.Image(id="1", name="1", creation_timestamp="1"),
                    compute_v1.Image(id="3", name="3", creation_timestamp="3"),
                ]
            ),
        ),
    )
    @mock.patch(MPATH + "GCE._get_name_filter", return_value="name-filter")
    @mock.patch(MPATH + "GCE._get_project", return_value="project-name")
    def test_daily_image_returns_latest_from_query(  # noqa: D102
        self,
        m_get_project,
        m_get_name_filter,
        m_query_image_list,
    ):
        gce = FakeGCE(tag="tag")
        image = gce.daily_image(
            "jammy", arch="x86_64", image_type=ImageType.GENERIC
        )
        assert m_get_project.call_args_list == [
            mock.call(image_type=ImageType.GENERIC)
        ]
        assert m_get_name_filter.call_args_list == [
            mock.call(release="jammy", image_type=ImageType.GENERIC)
        ]
        assert m_query_image_list.call_args_list == [
            mock.call("jammy", "project-name", "name-filter", "x86_64")
        ]
        assert image == "projects/project-name/global/images/4"
