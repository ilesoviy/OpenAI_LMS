"""
Tests for the LTI outcome service handlers, both in outcomes.py and in tasks.py
"""


from unittest.mock import MagicMock, patch

import ddt
from django.test import TestCase
from opaque_keys.edx.locator import BlockUsageLocator, CourseLocator

import lms.djangoapps.lti_provider.tasks as tasks
from common.djangoapps.student.tests.factories import UserFactory
from lms.djangoapps.lti_provider.models import GradedAssignment, LtiConsumer, OutcomeService


class BaseOutcomeTest(TestCase):
    """
    Super type for tests of both the leaf and composite outcome celery tasks.
    """
    def setUp(self):
        super().setUp()
        self.course_key = CourseLocator(
            org='some_org',
            course='some_course',
            run='some_run'
        )
        self.usage_key = BlockUsageLocator(
            course_key=self.course_key,
            block_type='problem',
            block_id='block_id'
        )
        self.user = UserFactory.create()
        self.consumer = LtiConsumer(
            consumer_name='Lti Consumer Name',
            consumer_key='consumer_key',
            consumer_secret='consumer_secret',
            instance_guid='tool_instance_guid'
        )
        self.consumer.save()
        outcome = OutcomeService(
            lis_outcome_service_url='http://example.com/service_url',
            lti_consumer=self.consumer
        )
        outcome.save()
        self.assignment = GradedAssignment(
            user=self.user,
            course_key=self.course_key,
            usage_key=self.usage_key,
            outcome_service=outcome,
            lis_result_sourcedid='sourcedid',
            version_number=1,
        )
        self.assignment.save()

        self.send_score_update_mock = self.setup_patch(
            'lms.djangoapps.lti_provider.outcomes.send_score_update', None
        )

    def setup_patch(self, function_name, return_value):
        """
        Patch a method with a given return value, and return the mock
        """
        mock = MagicMock(return_value=return_value)
        new_patch = patch(function_name, new=mock)
        new_patch.start()
        self.addCleanup(new_patch.stop)
        return mock


@ddt.ddt
class SendLeafOutcomeTest(BaseOutcomeTest):
    """
    Tests for the send_leaf_outcome method in tasks.py
    """

    @ddt.data(
        (2.0, 2.0, 1.0),
        (2.0, 0.0, 0.0),
        (1, 2, 0.5),
    )
    @ddt.unpack
    def test_outcome_with_score(self, earned, possible, expected):
        tasks.send_leaf_outcome(
            self.assignment.id,
            earned,
            possible
        )
        self.send_score_update_mock.assert_called_once_with(self.assignment, expected)


@ddt.ddt
class SendCompositeOutcomeTest(BaseOutcomeTest):
    """
    Tests for the send_composite_outcome method in tasks.py
    """

    def setUp(self):
        super().setUp()
        self.block = MagicMock()
        self.block.location = BlockUsageLocator(
            course_key=self.course_key,
            block_type='problem',
            block_id='problem',
        )
        self.course_grade = MagicMock()
        self.course_grade_mock = self.setup_patch(
            'lms.djangoapps.lti_provider.tasks.CourseGradeFactory.read', self.course_grade
        )
        self.module_store = MagicMock()
        self.module_store.get_item = MagicMock(return_value=self.block)
        self.check_result_mock = self.setup_patch(
            'lms.djangoapps.lti_provider.tasks.modulestore',
            self.module_store
        )

    @ddt.data(
        (2.0, 2.0, 1.0),
        (2.0, 0.0, 0.0),
        (1, 2, 0.5),
    )
    @ddt.unpack
    def test_outcome_with_score_score(self, earned, possible, expected):
        self.course_grade.score_for_block = MagicMock(return_value=(earned, possible))
        tasks.send_composite_outcome(
            self.user.id, str(self.course_key), self.assignment.id, 1
        )
        self.send_score_update_mock.assert_called_once_with(self.assignment, expected)

    def test_outcome_with_outdated_version(self):
        self.assignment.version_number = 2
        self.assignment.save()
        tasks.send_composite_outcome(
            self.user.id, str(self.course_key), self.assignment.id, 1
        )
        assert self.course_grade_mock.call_count == 0
