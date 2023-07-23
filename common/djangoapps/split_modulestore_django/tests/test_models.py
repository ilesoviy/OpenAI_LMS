""" Unit tests for SplitModulestoreCourseIndex """
from datetime import datetime

from bson.objectid import ObjectId
from django.test import TestCase
from opaque_keys.edx.keys import CourseKey

from common.djangoapps.split_modulestore_django.models import SplitModulestoreCourseIndex
from xmodule.modulestore import ModuleStoreEnum  # lint-amnesty, pylint: disable=wrong-import-order


class SplitModulestoreCourseIndexTest(TestCase):
    """ Unit tests for SplitModulestoreCourseIndex """

    def test_course_id_case_sensitive(self):
        """
        Make sure the course_id column is case sensitive.

        Although the platform code generally tries to prevent having two courses whose IDs differ only by case
        (e.g. https://git.io/J6voR , note `ignore_case=True`), we found at least one pair of courses on stage that
        differs only by case in its `org` ID (`edx` vs `edX`). So for backwards compatibility with MongoDB and to avoid
        issues for anyone else with similar course IDs that differ only by case, we've made the new version case
        sensitive too. The system still tries to prevent creation of courses that differ only by course (that hasn't
        changed), but now the MySQL version won't break if that has somehow happened.
        """
        course_index_common = {
            "course": "TL101",
            "run": "2015",
            "edited_by": ModuleStoreEnum.UserID.mgmt_command,
            "edited_on": datetime.now(),
            "last_update": datetime.now(),
            "versions": {},
            "schema_version": 1,
            "search_targets": {"wiki_slug": "TLslug"},
        }
        course_index_1 = {**course_index_common, "_id": ObjectId("553115a9d15a010b5c6f7228"), "org": "edx"}
        course_index_2 = {**course_index_common, "_id": ObjectId("550869e42d00970b5b082d2a"), "org": "edX"}
        data1 = SplitModulestoreCourseIndex.fields_from_v1_schema(course_index_1)
        data2 = SplitModulestoreCourseIndex.fields_from_v1_schema(course_index_2)
        SplitModulestoreCourseIndex(**data1).save()
        # This next line will fail if the course_id column is not case-sensitive:
        SplitModulestoreCourseIndex(**data2).save()
        # Also check deletion, to ensure the course_id historical record is not unique or case sensitive:
        SplitModulestoreCourseIndex.objects.get(course_id=CourseKey.from_string("course-v1:edx+TL101+2015")).delete()
        SplitModulestoreCourseIndex.objects.get(course_id=CourseKey.from_string("course-v1:edX+TL101+2015")).delete()
