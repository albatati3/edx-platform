""" API v0 views. """
from __future__ import absolute_import
import logging

from django.contrib.auth import get_user_model
from rest_condition import C
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from edx_rest_framework_extensions import permissions
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from edx_rest_framework_extensions.auth.session.authentication import SessionAuthenticationAllowInactiveUser
from lms.djangoapps.certificates.api import get_certificate_for_user, get_certificates_for_user
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.certificates.api import certificates_viewable_for_course
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.user_api.accounts.api import visible_fields
from openedx.core.lib.api.authentication import OAuth2AuthenticationAllowInactiveUser
import six


log = logging.getLogger(__name__)
User = get_user_model()


class CertificatesDetailView(GenericAPIView):
    """
        **Use Case**

            * Get the details of a certificate for a specific user in a course.

        **Example Request**

            GET /api/certificates/v0/certificates/{username}/courses/{course_id}

        **GET Parameters**

            A GET request must include the following parameters.

            * username: A string representation of an user's username.
            * course_id: A string representation of a Course ID.

        **GET Response Values**

            If the request for information about the Certificate is successful, an HTTP 200 "OK" response
            is returned.

            The HTTP 200 response has the following values.

            * username: A string representation of an user's username passed in the request.

            * course_id: A string representation of a Course ID.

            * certificate_type: A string representation of the certificate type.
                Can be honor|verified|professional

            * created_date: Date/time the certificate was created, in ISO-8661 format.

            * status: A string representation of the certificate status.

            * is_passing: True if the certificate has a passing status, False if not.

            * download_url: A string representation of the certificate url.

            * grade: A string representation of a float for the user's course grade.

        **Example GET Response**

            {
                "username": "bob",
                "course_id": "edX/DemoX/Demo_Course",
                "certificate_type": "verified",
                "created_date": "2015-12-03T13:14:28+0000",
                "status": "downloadable",
                "is_passing": true,
                "download_url": "http://www.example.com/cert.pdf",
                "grade": "0.98"
            }
    """

    authentication_classes = (
        JwtAuthentication,
        OAuth2AuthenticationAllowInactiveUser,
        SessionAuthenticationAllowInactiveUser,
    )

    permission_classes = (permissions.JWT_RESTRICTED_APPLICATION_OR_USER_ACCESS,)

    required_scopes = ['certificates:read']

    def get(self, request, username, course_id):
        """
        Gets a certificate information.

        Args:
            request (Request): Django request object.
            username (string): URI element specifying the user's username.
            course_id (string): URI element specifying the course location.

        Return:
            A JSON serialized representation of the certificate.
        """
        try:
            course_key = CourseKey.from_string(course_id)
        except InvalidKeyError:
            log.warning(u'Course ID string "%s" is not valid', course_id)
            return Response(
                status=404,
                data={'error_code': 'course_id_not_valid'}
            )

        user_cert = get_certificate_for_user(username=username, course_key=course_key)
        if user_cert is None:
            return Response(
                status=404,
                data={'error_code': 'no_certificate_for_user'}
            )
        return Response(
            {
                "username": user_cert.get('username'),
                "course_id": six.text_type(user_cert.get('course_key')),
                "certificate_type": user_cert.get('type'),
                "created_date": user_cert.get('created'),
                "status": user_cert.get('status'),
                "is_passing": user_cert.get('is_passing'),
                "download_url": user_cert.get('download_url'),
                "grade": user_cert.get('grade')
            }
        )


class CertificatesListView(GenericAPIView):
    """
        **Use Case**

            * Get the list of viewable course certificates for a specific user.

        **Example Request**

            GET /api/certificates/v0/certificates/{username}

        **GET Parameters**

            A GET request must include the following parameters.

            * username: A string representation of an user's username.

        **GET Response Values**

            If the request for information about the user's certificates is successful,
            an HTTP 200 "OK" response is returned.

            The HTTP 200 response contains a list of dicts with the following keys/values.

            * username: A string representation of an user's username passed in the request.

            * course_id: A string representation of a Course ID.

            * course_display_name: A string representation of the Course name.

            * course_organization: A string representation of the organization associated with the Course.

            * certificate_type: A string representation of the certificate type.
                Can be honor|verified|professional

            * created_date: Date/time the certificate was created, in ISO-8661 format.

            * status: A string representation of the certificate status.

            * is_passing: True if the certificate has a passing status, False if not.

            * download_url: A string representation of the certificate url.

            * grade: A string representation of a float for the user's course grade.

        **Example GET Response**

            [{
                "username": "bob",
                "course_id": "edX/DemoX/Demo_Course",
                "certificate_type": "verified",
                "created_date": "2015-12-03T13:14:28+0000",
                "status": "downloadable",
                "is_passing": true,
                "download_url": "http://www.example.com/cert.pdf",
                "grade": "0.98"
            }]
    """

    authentication_classes = (
        JwtAuthentication,
        OAuth2AuthenticationAllowInactiveUser,
        SessionAuthenticationAllowInactiveUser,
    )

    permission_classes = (
        C(IsAuthenticated) & (
            C(permissions.NotJwtRestrictedApplication) |
            (
                C(permissions.JwtRestrictedApplication) &
                permissions.JwtHasScope &
                permissions.JwtHasUserFilterForRequestedUser
            )
        ),
    )

    required_scopes = ['certificates:read']

    def get(self, request, username):
        """
        Gets the list of viewable course certificates for a specific user.

        Args:
            request (Request): Django request object.
            username (string): URI element specifying the user's username.

        Return:
            A JSON serialized representation of the list of certificates.
        """
        user_certs = []
        if self._viewable_by_requestor(request, username):
            for user_cert in self._get_certificates_for_user(username):
                user_certs.append({
                    'username': user_cert.get('username'),
                    'course_id': six.text_type(user_cert.get('course_key')),
                    'course_display_name': user_cert.get('course_display_name'),
                    'course_organization': user_cert.get('course_organization'),
                    'certificate_type': user_cert.get('type'),
                    'created_date': user_cert.get('created'),
                    'modified_date': user_cert.get('modified'),
                    'status': user_cert.get('status'),
                    'is_passing': user_cert.get('is_passing'),
                    'download_url': user_cert.get('download_url'),
                    'grade': user_cert.get('grade'),
                })

        return Response(user_certs)

    def _viewable_by_requestor(self, request, username):
        """
        Returns whether or not the requesting user is allowed to view the given user's certificates.
        """
        try:
            user = User.objects.select_related('profile').get(username=username)
        except User.DoesNotExist:
            return False

        is_owner = request.user.username == username
        is_staff = request.user.is_staff
        certificates_viewable = 'course_certificates' in visible_fields(user.profile, user)

        return is_owner or is_staff or certificates_viewable

    def _get_certificates_for_user(self, username):
        """
        Returns a user's viewable certificates sorted by course name.
        """
        course_certificates = get_certificates_for_user(username)
        passing_certificates = {}
        for course_certificate in course_certificates:
            if course_certificate.get('is_passing', False):
                course_key = course_certificate['course_key']
                passing_certificates[course_key] = course_certificate

        viewable_certificates = []
        for course_key, course_overview in CourseOverview.get_from_ids_if_exists(list(passing_certificates.keys())).items():
            if certificates_viewable_for_course(course_overview):
                course_certificate = passing_certificates[course_key]
                course_certificate['course_display_name'] = course_overview.display_name_with_default
                course_certificate['course_organization'] = course_overview.display_org_with_default
                viewable_certificates.append(course_certificate)

        viewable_certificates.sort(key=lambda certificate: certificate['created'])
        return viewable_certificates
