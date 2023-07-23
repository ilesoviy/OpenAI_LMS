"""
This file contains a management command for exporting the modulestore to
neo4j, a graph database.
"""


import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from edx_django_utils.cache import RequestCache
from edx_django_utils.monitoring import set_code_owner_attribute
from opaque_keys.edx.keys import CourseKey

import py2neo  # pylint: disable=unused-import
from py2neo import Graph, Node, Relationship

try:
    from py2neo.matching import NodeMatcher
except ImportError:
    from py2neo import NodeMatcher
else:
    pass


log = logging.getLogger(__name__)
celery_log = logging.getLogger('edx.celery.task')

# When testing locally, neo4j's bolt logger was noisy, so we'll only have it
# emit logs if there's an error.
bolt_log = logging.getLogger('neo4j.bolt')  # pylint: disable=invalid-name
bolt_log.setLevel(logging.ERROR)

PRIMITIVE_NEO4J_TYPES = (int, bytes, str, float, bool)


def serialize_item(item):
    """
    Args:
        item: an XBlock

    Returns:
        fields: a dictionary of an XBlock's field names and values
        block_type: the name of the XBlock's type (i.e. 'course'
        or 'problem')
    """
    from xmodule.modulestore.store_utilities import DETACHED_XBLOCK_TYPES

    # convert all fields to a dict and filter out parent and children field
    fields = {
        field: field_value.read_from(item)
        for (field, field_value) in item.fields.items()
        if field not in ['parent', 'children']
    }

    course_key = item.scope_ids.usage_id.course_key
    block_type = item.scope_ids.block_type

    # set or reset some defaults
    fields['edited_on'] = str(getattr(item, 'edited_on', ''))
    fields['display_name'] = item.display_name_with_default
    fields['org'] = course_key.org
    fields['course'] = course_key.course
    fields['run'] = course_key.run
    fields['course_key'] = str(course_key)
    fields['location'] = str(item.location)
    fields['block_type'] = block_type
    fields['detached'] = block_type in DETACHED_XBLOCK_TYPES

    if block_type == 'course':
        # prune the checklists field
        if 'checklists' in fields:
            del fields['checklists']

        # record the time this command was run
        fields['time_last_dumped_to_neo4j'] = str(timezone.now())

    return fields, block_type


def coerce_types(value):
    """
    Args:
        value: the value of an xblock's field

    Returns: either the value, a text version of the value, or, if the
        value is a list, a list where each element is converted to text.
    """
    coerced_value = value
    if isinstance(value, list):
        coerced_value = [str(element) for element in coerced_value]

    # if it's not one of the types that neo4j accepts,
    # just convert it to text
    elif not isinstance(value, PRIMITIVE_NEO4J_TYPES):
        coerced_value = str(value)

    return coerced_value


def add_to_transaction(neo4j_entities, transaction):
    """
    Args:
        neo4j_entities: a list of Nodes or Relationships
        transaction: a neo4j transaction
    """
    for entity in neo4j_entities:
        transaction.create(entity)


def get_command_last_run(course_key, graph):
    """
    This information is stored on the course node of a course in neo4j
    Args:
        course_key: a CourseKey
        graph: a py2neo Graph

    Returns: The datetime that the command was last run, converted into
        text, or None, if there's no record of this command last being run.
    """
    matcher = NodeMatcher(graph)
    course_node = matcher.match(
        "course",
        course_key=str(course_key)
    ).first()

    last_this_command_was_run = None
    if course_node:
        last_this_command_was_run = course_node['time_last_dumped_to_neo4j']

    return last_this_command_was_run


def get_course_last_published(course_key):
    """
    Approximately when was a course last published?

    We use the 'modified' column in the CourseOverview table as a quick and easy
    (although perhaps inexact) way of determining when a course was last
    published. This works because CourseOverview rows are re-written upon
    course publish.

    Args:
        course_key: a CourseKey

    Returns: The datetime the course was last published at, stringified.
        Uses Python's default str(...) implementation for datetimes, which
        is sortable and similar to ISO 8601:
        https://docs.python.org/3/library/datetime.html#datetime.date.__str__
    """
    # Import is placed here to avoid model import at project startup.
    from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

    approx_last_published = CourseOverview.get_from_id(course_key).modified
    return str(approx_last_published)


def strip_branch_and_version(location):
    """
    Removes the branch and version information from a location.
    Args:
        location: an xblock's location.
    Returns: that xblock's location without branch and version information.
    """
    return location.for_branch(None)


def serialize_course(course_id):
    """
    Serializes a course into py2neo Nodes and Relationships
    Args:
        course_id: CourseKey of the course we want to serialize

    Returns:
        nodes: a list of py2neo Node objects
        relationships: a list of py2neo Relationships objects
    """
    # Import is placed here to avoid model import at project startup.
    from xmodule.modulestore.django import modulestore

    # create a location to node mapping we'll need later for
    # writing relationships
    location_to_node = {}
    items = modulestore().get_items(course_id)

    # create nodes
    for item in items:
        fields, block_type = serialize_item(item)

        for field_name, value in fields.items():
            fields[field_name] = coerce_types(value)

        node = Node(block_type, 'item', **fields)
        location_to_node[strip_branch_and_version(item.location)] = node

    # create relationships
    relationships = []
    for item in items:
        previous_child_node = None
        for index, child in enumerate(item.get_children()):
            parent_node = location_to_node.get(strip_branch_and_version(item.location))
            child_node = location_to_node.get(strip_branch_and_version(child.location))

            if parent_node is not None and child_node is not None:
                child_node["index"] = index

                relationship = Relationship(parent_node, "PARENT_OF", child_node)
                relationships.append(relationship)

                if previous_child_node:
                    ordering_relationship = Relationship(
                        previous_child_node,
                        "PRECEDES",
                        child_node,
                    )
                    relationships.append(ordering_relationship)
                previous_child_node = child_node

    nodes = list(location_to_node.values())
    return nodes, relationships


def should_dump_course(course_key, graph):
    """
    Only dump the course if it's been changed since the last time it's been
    dumped.
    Args:
        course_key: a CourseKey object.
        graph: a py2neo Graph object.

    Returns:
        - whether this course should be dumped to neo4j (bool)
        - reason why course needs to be dumped (string, None if doesn't need to be dumped)
    """

    last_this_command_was_run = get_command_last_run(course_key, graph)

    course_last_published_date = get_course_last_published(course_key)

    # if we don't have a record of the last time this command was run,
    # we should serialize the course and dump it
    if last_this_command_was_run is None:
        return (
            True,
            "no record of the last neo4j update time for the course"
        )

    # if we've serialized the course recently and we have no published
    # events, we will not dump it, and so we can skip serializing it
    # again here
    if last_this_command_was_run and course_last_published_date is None:
        return (False, None)

    # otherwise, serialize and dump the course if the command was run
    # before the course's last published event
    needs_update = last_this_command_was_run < course_last_published_date
    update_reason = None
    if needs_update:
        update_reason = (
            f"course has been published since last neo4j update time - "
            f"update date {last_this_command_was_run} < published date {course_last_published_date}"
        )
    return (needs_update, update_reason)


@shared_task
@set_code_owner_attribute
def dump_course_to_neo4j(course_key_string, connection_overrides=None):
    """
    Serializes a course and writes it to neo4j.

    Arguments:
        course_key_string: course key for the course to be exported
        connection_overrides (dict):  overrides to Neo4j connection
            parameters specified in `settings.COURSEGRAPH_CONNECTION`.
    """
    course_key = CourseKey.from_string(course_key_string)
    nodes, relationships = serialize_course(course_key)
    celery_log.info(
        "Now dumping %s to neo4j: %d nodes and %d relationships",
        course_key,
        len(nodes),
        len(relationships),
    )

    graph = authenticate_and_create_graph(
        connection_overrides=connection_overrides
    )

    transaction = graph.begin()
    course_string = str(course_key)
    try:
        # first, delete existing course
        transaction.run(
            "MATCH (n:item) WHERE n.course_key='{}' DETACH DELETE n".format(
                course_string
            )
        )

        # now, re-add it
        add_to_transaction(nodes, transaction)
        add_to_transaction(relationships, transaction)
        graph.commit(transaction)
        celery_log.info("Completed dumping %s to neo4j", course_key)

    except Exception:  # pylint: disable=broad-except
        celery_log.exception(
            "Error trying to dump course %s to neo4j, rolling back",
            course_string
        )
        graph.rollback(transaction)


class ModuleStoreSerializer:
    """
    Class with functionality to serialize a modulestore into subgraphs,
    one graph per course.
    """

    def __init__(self, course_keys):
        self.course_keys = course_keys

    @classmethod
    def create(cls, courses=None, skip=None):
        """
        Sets the object's course_keys attribute from the `courses` parameter.
        If that parameter isn't furnished, loads all course_keys from the
        modulestore.
        Filters out course_keys in the `skip` parameter, if provided.
        Args:
            courses: A list of string serializations of course keys.
                For example, ["course-v1:org+course+run"].
            skip: Also a list of string serializations of course keys.
        """
        # Import is placed here to avoid model import at project startup.
        from xmodule.modulestore.django import modulestore
        if courses:
            course_keys = [CourseKey.from_string(course.strip()) for course in courses]
        else:
            course_keys = [
                course.id for course in modulestore().get_course_summaries()
            ]
        if skip is not None:
            skip_keys = [CourseKey.from_string(course.strip()) for course in skip]
            course_keys = [course_key for course_key in course_keys if course_key not in skip_keys]
        return cls(course_keys)

    def dump_courses_to_neo4j(self, connection_overrides=None, override_cache=False):
        """
        Method that iterates through a list of courses in a modulestore,
        serializes them, then submits tasks to write them to neo4j.
        Arguments:
            connection_overrides (dict): overrides to Neo4j connection
                parameters specified in `settings.COURSEGRAPH_CONNECTION`.
            override_cache: serialize the courses even if they'be been recently
                serialized

        Returns: two lists--one of the courses that were successfully written
            to neo4j and one of courses that were not.
        """

        total_number_of_courses = len(self.course_keys)

        submitted_courses = []
        skipped_courses = []

        graph = authenticate_and_create_graph(connection_overrides)

        for index, course_key in enumerate(self.course_keys):
            # first, clear the request cache to prevent memory leaks
            RequestCache.clear_all_namespaces()

            (needs_dump, reason) = should_dump_course(course_key, graph)
            if not (override_cache or needs_dump):
                log.info("skipping submitting %s, since it hasn't changed", course_key)
                skipped_courses.append(str(course_key))
                continue

            if override_cache:
                reason = "override_cache is True"

            log.info(
                "Now submitting %s for export to neo4j, because %s: course %d of %d total courses",
                course_key,
                reason,
                index + 1,
                total_number_of_courses,
            )

            dump_course_to_neo4j.apply_async(
                kwargs=dict(
                    course_key_string=str(course_key),
                    connection_overrides=connection_overrides,
                )
            )
            submitted_courses.append(str(course_key))

        return submitted_courses, skipped_courses


def authenticate_and_create_graph(connection_overrides=None):
    """
    This function authenticates with neo4j and creates a py2neo graph object

    Arguments:
        connection_overrides (dict): overrides to Neo4j connection
            parameters specified in `settings.COURSEGRAPH_CONNECTION`.

    Returns: a py2neo `Graph` object.
    """
    provided_overrides = {
        key: value
        for key, value in (connection_overrides or {}).items()
        # Drop overrides whose values are `None`. Note that `False` is a
        # legitimate override value that we don't want to drop here.
        if value is not None
    }
    connection_with_overrides = {**settings.COURSEGRAPH_CONNECTION, **provided_overrides}
    return Graph(**connection_with_overrides)
