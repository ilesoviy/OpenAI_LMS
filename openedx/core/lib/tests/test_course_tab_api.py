"""
Tests for the plugin API
"""
import pytest
from django.test import TestCase
from edx_django_utils.plugins import PluginError

from openedx.core.lib.course_tabs import CourseTabPluginManager


class TestCourseTabApi(TestCase):
    """
    Unit tests for the course tab plugin API
    """

    def test_get_plugin(self):
        """
        Verify that get_plugin works as expected.
        """
        tab_type = CourseTabPluginManager.get_plugin("instructor")
        assert tab_type.title == 'Instructor'

        with pytest.raises(PluginError):
            CourseTabPluginManager.get_plugin("no_such_type")
