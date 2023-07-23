"""
Classes used to model the roles used in the courseware. Each role is responsible for checking membership,
adding users, removing users, and listing members
"""


import logging
from abc import ABCMeta, abstractmethod
from collections import defaultdict

from django.contrib.auth.models import User  # lint-amnesty, pylint: disable=imported-auth-user
from opaque_keys.edx.django.models import CourseKeyField

from openedx.core.lib.cache_utils import get_cache
from common.djangoapps.student.models import CourseAccessRole

log = logging.getLogger(__name__)

# A list of registered access roles.
REGISTERED_ACCESS_ROLES = {}


def register_access_role(cls):
    """
    Decorator that allows access roles to be registered within the roles module and referenced by their
    string values.

    Assumes that the decorated class has a "ROLE" attribute, defining its type.

    """
    try:
        role_name = cls.ROLE
        REGISTERED_ACCESS_ROLES[role_name] = cls
    except AttributeError:
        log.exception("Unable to register Access Role with attribute 'ROLE'.")
    return cls


class BulkRoleCache:  # lint-amnesty, pylint: disable=missing-class-docstring
    CACHE_NAMESPACE = "student.roles.BulkRoleCache"
    CACHE_KEY = 'roles_by_user'

    @classmethod
    def prefetch(cls, users):  # lint-amnesty, pylint: disable=missing-function-docstring
        roles_by_user = defaultdict(set)
        get_cache(cls.CACHE_NAMESPACE)[cls.CACHE_KEY] = roles_by_user

        for role in CourseAccessRole.objects.filter(user__in=users).select_related('user'):
            roles_by_user[role.user.id].add(role)

        users_without_roles = [u for u in users if u.id not in roles_by_user]
        for user in users_without_roles:
            roles_by_user[user.id] = set()

    @classmethod
    def get_user_roles(cls, user):
        return get_cache(cls.CACHE_NAMESPACE)[cls.CACHE_KEY][user.id]


class RoleCache:
    """
    A cache of the CourseAccessRoles held by a particular user
    """
    def __init__(self, user):
        try:
            self._roles = BulkRoleCache.get_user_roles(user)
        except KeyError:
            self._roles = set(
                CourseAccessRole.objects.filter(user=user).all()
            )

    def has_role(self, role, course_id, org):
        """
        Return whether this RoleCache contains a role with the specified role, course_id, and org
        """
        return any(
            access_role.role == role and
            access_role.course_id == course_id and
            access_role.org == org
            for access_role in self._roles
        )


class AccessRole(metaclass=ABCMeta):
    """
    Object representing a role with particular access to a resource
    """

    @abstractmethod
    def has_user(self, user):
        """
        Return whether the supplied django user has access to this role.
        """
        return False

    @abstractmethod
    def add_users(self, *users):
        """
        Add the role to the supplied django users.
        """
        pass  # lint-amnesty, pylint: disable=unnecessary-pass

    @abstractmethod
    def remove_users(self, *users):
        """
        Remove the role from the supplied django users.
        """
        pass  # lint-amnesty, pylint: disable=unnecessary-pass

    @abstractmethod
    def users_with_role(self):
        """
        Return a django QuerySet for all of the users with this role
        """
        return User.objects.none()


class GlobalStaff(AccessRole):
    """
    The global staff role
    """
    def has_user(self, user):
        return bool(user and user.is_staff)

    def add_users(self, *users):
        for user in users:
            if user.is_authenticated and user.is_active:
                user.is_staff = True
                user.save()

    def remove_users(self, *users):
        for user in users:
            # don't check is_authenticated nor is_active on purpose
            user.is_staff = False
            user.save()

    def users_with_role(self):
        raise Exception("This operation is un-indexed, and shouldn't be used")


class RoleBase(AccessRole):
    """
    Roles by type (e.g., instructor, beta_user) and optionally org, course_key
    """
    def __init__(self, role_name, org='', course_key=None):
        """
        Create role from required role_name w/ optional org and course_key. You may just provide a role
        name if it's a global role (not constrained to an org or course). Provide org if constrained to
        an org. Provide org and course if constrained to a course. Although, you should use the subclasses
        for all of these.
        """
        super().__init__()

        self.org = org
        self.course_key = course_key
        self._role_name = role_name

    # pylint: disable=arguments-differ
    def has_user(self, user, check_user_activation=True):
        """
        Check if the supplied django user has access to this role.

        Arguments:
            user: user to check against access to role
            check_user_activation: Indicating whether or not we need to check
                user activation while checking user roles
        Return:
            bool identifying if user has that particular role or not
        """
        if check_user_activation and not (user.is_authenticated and user.is_active):
            return False

        # pylint: disable=protected-access
        if not hasattr(user, '_roles'):
            # Cache a list of tuples identifying the particular roles that a user has
            # Stored as tuples, rather than django models, to make it cheaper to construct objects for comparison
            user._roles = RoleCache(user)

        return user._roles.has_role(self._role_name, self.course_key, self.org)

    def add_users(self, *users):
        """
        Add the supplied django users to this role.
        """
        # silently ignores anonymous and inactive users so that any that are
        # legit get updated.
        from common.djangoapps.student.models import CourseAccessRole  # lint-amnesty, pylint: disable=redefined-outer-name, reimported
        for user in users:
            if user.is_authenticated and user.is_active and not self.has_user(user):
                entry = CourseAccessRole(user=user, role=self._role_name, course_id=self.course_key, org=self.org)
                entry.save()
                if hasattr(user, '_roles'):
                    del user._roles

    def remove_users(self, *users):
        """
        Remove the supplied django users from this role.
        """
        entries = CourseAccessRole.objects.filter(
            user__in=users, role=self._role_name, org=self.org, course_id=self.course_key
        )
        entries.delete()
        for user in users:
            if hasattr(user, '_roles'):
                del user._roles

    def users_with_role(self):
        """
        Return a django QuerySet for all of the users with this role
        """
        # Org roles don't query by CourseKey, so use CourseKeyField.Empty for that query
        if self.course_key is None:
            self.course_key = CourseKeyField.Empty
        entries = User.objects.filter(
            courseaccessrole__role=self._role_name,
            courseaccessrole__org=self.org,
            courseaccessrole__course_id=self.course_key
        )
        return entries

    def get_orgs_for_user(self, user):
        """
        Returns a list of org short names for the user with given role.
        """
        return CourseAccessRole.objects.filter(user=user, role=self._role_name).values_list('org', flat=True)


class CourseRole(RoleBase):
    """
    A named role in a particular course
    """
    def __init__(self, role, course_key):
        """
        Args:
            course_key (CourseKey)
        """
        super().__init__(role, course_key.org, course_key)

    @classmethod
    def course_group_already_exists(self, course_key):  # lint-amnesty, pylint: disable=bad-classmethod-argument
        return CourseAccessRole.objects.filter(org=course_key.org, course_id=course_key).exists()

    def __repr__(self):
        return f'<{self.__class__.__name__}: course_key={self.course_key}>'


class OrgRole(RoleBase):
    """
    A named role in a particular org independent of course
    """
    def __repr__(self):
        return f'<{self.__class__.__name__}>'


@register_access_role
class CourseStaffRole(CourseRole):
    """A Staff member of a course"""
    ROLE = 'staff'

    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


@register_access_role
class CourseInstructorRole(CourseRole):
    """A course Instructor"""
    ROLE = 'instructor'

    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


@register_access_role
class CourseFinanceAdminRole(CourseRole):
    """A course staff member with privileges to review financial data."""
    ROLE = 'finance_admin'

    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


@register_access_role
class CourseSalesAdminRole(CourseRole):
    """A course staff member with privileges to perform sales operations. """
    ROLE = 'sales_admin'

    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


@register_access_role
class CourseBetaTesterRole(CourseRole):
    """A course Beta Tester"""
    ROLE = 'beta_testers'

    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


@register_access_role
class LibraryUserRole(CourseRole):
    """
    A user who can view a library and import content from it, but not edit it.
    Used in Studio only.
    """
    ROLE = 'library_user'

    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


class CourseCcxCoachRole(CourseRole):
    """A CCX Coach"""
    ROLE = 'ccx_coach'

    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


@register_access_role
class CourseDataResearcherRole(CourseRole):
    """A Data Researcher"""
    ROLE = 'data_researcher'

    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


class OrgStaffRole(OrgRole):
    """An organization staff member"""
    def __init__(self, *args, **kwargs):
        super().__init__('staff', *args, **kwargs)


class OrgInstructorRole(OrgRole):
    """An organization instructor"""
    def __init__(self, *args, **kwargs):
        super().__init__('instructor', *args, **kwargs)


@register_access_role
class OrgContentCreatorRole(OrgRole):
    """An organization content creator"""

    ROLE = "org_course_creator_group"

    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


class OrgLibraryUserRole(OrgRole):
    """
    A user who can view any libraries in an org and import content from them, but not edit them.
    Used in Studio only.
    """
    ROLE = LibraryUserRole.ROLE

    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


class OrgDataResearcherRole(OrgRole):
    """A Data Researcher"""
    ROLE = 'data_researcher'

    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


@register_access_role
class CourseCreatorRole(RoleBase):
    """
    This is the group of people who have permission to create new courses (we may want to eventually
    make this an org based role).
    """
    ROLE = "course_creator_group"

    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


@register_access_role
class SupportStaffRole(RoleBase):
    """
    Student support team members.
    """
    ROLE = "support"

    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


class UserBasedRole:
    """
    Backward mapping: given a user, manipulate the courses and roles
    """
    def __init__(self, user, role):
        """
        Create a UserBasedRole accessor: for a given user and role (e.g., "instructor")
        """
        self.user = user
        self.role = role

    def has_course(self, course_key):
        """
        Return whether the role's user has the configured role access to the passed course
        """
        if not (self.user.is_authenticated and self.user.is_active):
            return False

        # pylint: disable=protected-access
        if not hasattr(self.user, '_roles'):
            self.user._roles = RoleCache(self.user)

        return self.user._roles.has_role(self.role, course_key, course_key.org)

    def add_course(self, *course_keys):
        """
        Grant this object's user the object's role for the supplied courses
        """
        if self.user.is_authenticated and self.user.is_active:
            for course_key in course_keys:
                entry = CourseAccessRole(user=self.user, role=self.role, course_id=course_key, org=course_key.org)
                entry.save()
            if hasattr(self.user, '_roles'):
                del self.user._roles
        else:
            raise ValueError("user is not active. Cannot grant access to courses")

    def remove_courses(self, *course_keys):
        """
        Remove the supplied courses from this user's configured role.
        """
        entries = CourseAccessRole.objects.filter(user=self.user, role=self.role, course_id__in=course_keys)
        entries.delete()
        if hasattr(self.user, '_roles'):
            del self.user._roles

    def courses_with_role(self):
        """
        Return a django QuerySet for all of the courses with this user x role. You can access
        any of these properties on each result record:
        * user (will be self.user--thus uninteresting)
        * org
        * course_id
        * role (will be self.role--thus uninteresting)
        """
        return CourseAccessRole.objects.filter(role=self.role, user=self.user)
