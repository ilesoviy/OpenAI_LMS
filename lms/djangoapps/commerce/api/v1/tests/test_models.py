""" Tests for models. """


import ddt
from django.test import TestCase

from common.djangoapps.course_modes.models import CourseMode

from ..models import Course


@ddt.ddt
class CourseTests(TestCase):
    """ Tests for Course model. """

    def setUp(self):
        super().setUp()
        self.course = Course('a/b/c', [])

    @ddt.unpack
    @ddt.data(
        ('credit', 'Credit'),
        ('professional', 'Professional Education'),
        ('no-id-professional', 'Professional Education'),
        ('verified', 'Verified Certificate'),
        ('honor', 'Honor Certificate'),
        ('audit', 'Audit'),
    )
    def test_get_mode_display_name(self, slug, expected_display_name):
        """ Verify the method properly maps mode slugs to display names. """
        mode = CourseMode(mode_slug=slug)
        assert self.course.get_mode_display_name(mode) == expected_display_name

    def test_get_mode_display_name_unknown_slug(self):
        """ Verify the method returns the slug if it has no known mapping. """
        mode = CourseMode(mode_slug='Blah!')
        assert self.course.get_mode_display_name(mode) == mode.mode_slug
