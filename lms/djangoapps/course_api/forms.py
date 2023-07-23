"""
Course API forms
"""


from collections import namedtuple

from django.core.exceptions import ValidationError
from django.forms import CharField, Form
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

from openedx.core.djangoapps.util.forms import (
    ExtendedNullBooleanField,
    MultiValueField
)


class UsernameValidatorMixin:
    """
    Mixin class for validating the username parameter.
    """

    def clean_username(self):
        """
        Ensures the username is provided unless the request is made
        as an anonymous user.
        """
        username = self.cleaned_data.get('username')
        return username or ''


class CourseDetailGetForm(UsernameValidatorMixin, Form):
    """
    A form to validate query parameters in the course detail endpoint
    """
    username = CharField(required=False)
    course_key = CharField(required=True)

    def clean_course_key(self):
        """
        Ensure a valid `course_key` was provided.
        """
        course_key_string = self.cleaned_data['course_key']
        try:
            return CourseKey.from_string(course_key_string)
        except InvalidKeyError:
            raise ValidationError(f"'{str(course_key_string)}' is not a valid course key.")  # lint-amnesty, pylint: disable=raise-missing-from


class CourseListGetForm(UsernameValidatorMixin, Form):
    """
    A form to validate query parameters in the course list retrieval endpoint
    """
    search_term = CharField(required=False)
    username = CharField(required=False)
    org = CharField(required=False)

    # white list of all supported filter fields
    filter_type = namedtuple('filter_type', ['param_name', 'field_name'])
    supported_filters = [
        filter_type(param_name='mobile', field_name='mobile_available'),
    ]
    mobile = ExtendedNullBooleanField(required=False)
    active_only = ExtendedNullBooleanField(required=False)
    permissions = MultiValueField(required=False)

    def clean(self):
        """
        Return cleaned data, including additional filters.
        """
        cleaned_data = super().clean()

        # create a filter for all supported filter fields
        filter_ = {}
        for supported_filter in self.supported_filters:
            if cleaned_data.get(supported_filter.param_name) is not None:
                filter_[supported_filter.field_name] = cleaned_data[supported_filter.param_name]
        cleaned_data['filter_'] = filter_ or None

        return cleaned_data


class CourseIdListGetForm(UsernameValidatorMixin, Form):
    """
    A form to validate query parameters in the course list retrieval endpoint
    """
    username = CharField(required=False)
    role = CharField(required=True)
