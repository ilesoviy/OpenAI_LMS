"""
Tests for minimum grade requirement status
"""


from datetime import datetime, timedelta

from unittest.mock import MagicMock
import ddt
import pytz
from django.test.client import RequestFactory

from common.djangoapps.course_modes.models import CourseMode
from openedx.core.djangoapps.credit.api import get_credit_requirement_status, set_credit_requirements
from openedx.core.djangoapps.credit.models import CreditCourse, CreditProvider
from openedx.core.djangoapps.credit.signals import listen_for_grade_calculation
from openedx.core.djangolib.testing.utils import skip_unless_lms
from common.djangoapps.student.models import CourseEnrollment
from common.djangoapps.student.tests.factories import UserFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase  # lint-amnesty, pylint: disable=wrong-import-order
from xmodule.modulestore.tests.factories import CourseFactory  # lint-amnesty, pylint: disable=wrong-import-order


@skip_unless_lms
@ddt.ddt
class TestMinGradedRequirementStatus(ModuleStoreTestCase):
    """Test cases to check the minimum grade requirement status updated.
    If user grade is above or equal to min-grade then status will be
    satisfied. But if student grade is less than and deadline is passed then
    user will be marked as failed.
    """
    VALID_DUE_DATE = datetime.now(pytz.UTC) + timedelta(days=20)
    EXPIRED_DUE_DATE = datetime.now(pytz.UTC) - timedelta(days=20)

    DATES = {
        'valid': VALID_DUE_DATE,
        'expired': EXPIRED_DUE_DATE,
        None: None,
    }

    def setUp(self):
        super().setUp()
        self.course = CourseFactory.create(
            org='Robot', number='999', display_name='Test Course'
        )

        self.user = UserFactory()
        self.request = RequestFactory().get('/')
        self.request.user = self.user
        self.client.login(username=self.user.username, password=self.user.password)

        # Enable the course for credit
        CreditCourse.objects.create(
            course_key=self.course.id,
            enabled=True,
        )

        # Configure a credit provider for the course
        CreditProvider.objects.create(
            provider_id="ASU",
            enable_integration=True,
            provider_url="https://credit.example.com/request",
        )

        requirements = [{
            "namespace": "grade",
            "name": "grade",
            "display_name": "Grade",
            "criteria": {"min_grade": 0.52},
        }]
        # Add a single credit requirement (final grade)
        set_credit_requirements(self.course.id, requirements)

        # Enroll user in verified mode.
        self.enrollment = CourseEnrollment.enroll(self.user, self.course.id, mode=CourseMode.VERIFIED)

    def assert_requirement_status(self, grade, due_date, expected_status):
        """ Verify the user's credit requirement status is as expected after simulating a grading calculation. """
        course_grade = MagicMock()
        course_grade.percent = grade
        listen_for_grade_calculation(None, self.user, course_grade, self.course.id, due_date)
        req_status = get_credit_requirement_status(self.course.id, self.request.user.username, 'grade', 'grade')

        assert req_status[0]['status'] == expected_status

        if expected_status == 'satisfied':
            expected_reason = {'final_grade': grade}
            assert req_status[0]['reason'] == expected_reason

    @ddt.data(
        (0.6, 'valid'),
        (0.52, None),
    )
    @ddt.unpack
    def test_min_grade_requirement_with_valid_grade(self, grade, due_date_name):
        """Test with valid grades submitted before deadline"""
        self.assert_requirement_status(grade, self.DATES[due_date_name], 'satisfied')

    def test_grade_changed(self):
        """ Verify successive calls to update a satisfied grade requirement are recorded. """
        self.assert_requirement_status(0.6, self.VALID_DUE_DATE, 'satisfied')
        self.assert_requirement_status(0.75, self.VALID_DUE_DATE, 'satisfied')
        self.assert_requirement_status(0.70, self.VALID_DUE_DATE, 'satisfied')

    def test_min_grade_requirement_with_valid_grade_and_expired_deadline(self):
        """ Verify the status is set to failure if a passing grade is received past the submission deadline. """
        self.assert_requirement_status(0.70, self.EXPIRED_DUE_DATE, 'failed')

    @ddt.data(
        (0.50, None),
        (0.51, None),
        (0.40, 'valid'),
    )
    @ddt.unpack
    def test_min_grade_requirement_failed_grade_valid_deadline(self, grade, due_date_name):
        """Test with failed grades and deadline is still open or not defined."""
        self.assert_requirement_status(grade, self.DATES[due_date_name], None)

    def test_min_grade_requirement_failed_grade_expired_deadline(self):
        """Test with failed grades and deadline expire"""
        self.assert_requirement_status(0.22, self.EXPIRED_DUE_DATE, 'failed')

    @ddt.data(
        CourseMode.AUDIT,
        CourseMode.HONOR,
        CourseMode.CREDIT_MODE
    )
    def test_requirement_failed_for_non_verified_enrollment(self, mode):
        """Test with valid grades submitted before deadline with non-verified enrollment."""
        self.enrollment.update_enrollment(mode, True)
        self.assert_requirement_status(0.8, self.VALID_DUE_DATE, None)
