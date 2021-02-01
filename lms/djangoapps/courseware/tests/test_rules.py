"""
Tests for permissions defined in courseware.rules
"""


import ddt
import six
from django.test import TestCase
from django.test.utils import override_settings
from opaque_keys.edx.locator import CourseLocator

from common.djangoapps.course_modes.tests.factories import CourseModeFactory
from common.djangoapps.student.models import CourseEnrollment
from common.djangoapps.student.tests.factories import UserFactory


@ddt.ddt
class PermissionTests(TestCase):
    """
    Tests for permissions defined in courseware.rules
    """
    def setUp(self):
        super(PermissionTests, self).setUp()  # lint-amnesty, pylint: disable=super-with-arguments
        self.user = UserFactory()

        self.course_id = CourseLocator('MITx', '000', 'Perm_course')
        CourseModeFactory(mode_slug='verified', course_id=self.course_id)
        CourseModeFactory(mode_slug='masters', course_id=self.course_id)
        CourseModeFactory(mode_slug='professional', course_id=self.course_id)
        CourseEnrollment.unenroll(self.user, self.course_id)

    def tearDown(self):
        super(PermissionTests, self).tearDown()  # lint-amnesty, pylint: disable=super-with-arguments
        self.user.delete()

    @ddt.data(
        (None, False),
        ('audit', False),
        ('verified', True),
        ('masters', True),
        ('professional', True),
        ('no-id-professional', False),
    )
    @ddt.unpack
    def test_proctoring_perm(self, mode, should_have_perm):
        """
        Test that the user has the edx_proctoring.can_take_proctored_exam permission
        """
        if mode is not None:
            CourseEnrollment.enroll(self.user, self.course_id, mode=mode)
        has_perm = self.user.has_perm('edx_proctoring.can_take_proctored_exam',
                                      {'course_id': six.text_type(self.course_id)})
        assert has_perm == should_have_perm

    @override_settings(
        PROCTORING_BACKENDS={
            'mock_proctoring_allow_honor_mode': {
                'allow_honor_mode': True,
            },
        }
    )
    def test_proctoring_perm_with_honor_mode_permission(self):
        """
        Test that the user has the edx_proctoring.can_take_proctored_exam permission in honor enrollment mode.

        If proctoring backend configuration allows exam in honor mode {`allow_honor_mode`: True} the user is
        granter proctored exam permission.
        """
        CourseEnrollment.enroll(self.user, self.course_id, mode='honor')
        self.assertTrue(self.user.has_perm(
            'edx_proctoring.can_take_proctored_exam', {
                'course_id': six.text_type(self.course_id),
                'backend': 'mock_proctoring_allow_honor_mode',
                'is_proctored': True
            }
        ))
