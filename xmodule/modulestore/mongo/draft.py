"""
A ModuleStore that knows about a special version DRAFT. Blocks
marked as DRAFT are read in preference to blocks without the DRAFT
version by this ModuleStore (so, access to i4x://org/course/cat/name
returns the i4x://org/course/cat/name@draft object if that exists,
and otherwise returns i4x://org/course/cat/name).
"""


import logging

import pymongo
from opaque_keys.edx.keys import UsageKey
from opaque_keys.edx.locator import BlockUsageLocator
from xblock.core import XBlock

from openedx.core.lib.cache_utils import request_cached
from xmodule.exceptions import InvalidVersionError
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.draft_and_published import DIRECT_ONLY_CATEGORIES, UnsupportedRevisionError
from xmodule.modulestore.exceptions import (
    DuplicateCourseError,
    DuplicateItemError,
    InvalidBranchSetting,
    ItemNotFoundError
)
from xmodule.modulestore.mongo.base import (
    SORT_REVISION_FAVOR_DRAFT,
    MongoModuleStore,
    MongoRevisionKey,
    as_draft,
    as_published
)
from xmodule.modulestore.store_utilities import rewrite_nonportable_content_links

log = logging.getLogger(__name__)


def wrap_draft(item):
    """
    Cleans the item's location and sets the `is_draft` attribute if needed.

    Sets `item.is_draft` to `True` if the item is DRAFT, and `False` otherwise.
    Sets the item's location to the non-draft location in either case.
    """
    item.is_draft = (item.location.branch == MongoRevisionKey.draft)
    item.location = item.location.replace(revision=MongoRevisionKey.published)
    return item


class DraftModuleStore(MongoModuleStore):
    """
    This mixin modifies a modulestore to give it draft semantics.
    Edits made to units are stored to locations that have the revision DRAFT.
    Reads are first read with revision DRAFT, and then fall back
    to the baseline revision only if DRAFT doesn't exist.

    This module store also includes functionality to promote DRAFT blocks (and their children)
    to published blocks.
    """
    def get_item(self, usage_key, depth=0, revision=None, using_descriptor_system=None, **kwargs):  # lint-amnesty, pylint: disable=arguments-differ
        """
        Returns an XModuleDescriptor instance for the item at usage_key.

        Args:
            usage_key: A :class:`.UsageKey` instance

            depth (int): An argument that some module stores may use to prefetch
                descendants of the queried blocks for more efficient results later
                in the request. The depth is counted in the number of calls to
                get_children() to cache.  None indicates to cache all descendants.

            revision:
                ModuleStoreEnum.RevisionOption.published_only - returns only the published item.
                ModuleStoreEnum.RevisionOption.draft_only - returns only the draft item.
                None - uses the branch setting as follows:
                    if branch setting is ModuleStoreEnum.Branch.published_only, returns only the published item.
                    if branch setting is ModuleStoreEnum.Branch.draft_preferred, returns either draft or published item,
                        preferring draft.

                Note: If the item is in DIRECT_ONLY_CATEGORIES, then returns only the PUBLISHED
                version regardless of the revision.

            using_descriptor_system (CachingDescriptorSystem): The existing CachingDescriptorSystem
                to add data to, and to load the XBlocks from.

        Raises:
            xmodule.modulestore.exceptions.InsufficientSpecificationError
            if any segment of the usage_key is None except revision

            xmodule.modulestore.exceptions.ItemNotFoundError if no object
            is found at that usage_key
        """
        def get_published():
            return wrap_draft(super(DraftModuleStore, self).get_item(  # lint-amnesty, pylint: disable=super-with-arguments
                usage_key, depth=depth, using_descriptor_system=using_descriptor_system,
                for_parent=kwargs.get('for_parent'),
            ))

        def get_draft():
            return wrap_draft(super(DraftModuleStore, self).get_item(  # lint-amnesty, pylint: disable=super-with-arguments
                as_draft(usage_key), depth=depth, using_descriptor_system=using_descriptor_system,
                for_parent=kwargs.get('for_parent')
            ))

        # return the published version if ModuleStoreEnum.RevisionOption.published_only is requested
        if revision == ModuleStoreEnum.RevisionOption.published_only:
            return get_published()

        # if the item is direct-only, there can only be a published version
        elif usage_key.block_type in DIRECT_ONLY_CATEGORIES:
            return get_published()

        # return the draft version (without any fallback to PUBLISHED) if DRAFT-ONLY is requested
        elif revision == ModuleStoreEnum.RevisionOption.draft_only:
            return get_draft()

        elif self.get_branch_setting() == ModuleStoreEnum.Branch.published_only:
            return get_published()

        elif revision is None:
            # could use a single query wildcarding revision and sorting by revision. would need to
            # use prefix form of to_deprecated_son
            try:
                # first check for a draft version
                return get_draft()
            except ItemNotFoundError:
                # otherwise, fall back to the published version
                return get_published()

        else:
            raise UnsupportedRevisionError()

    def has_item(self, usage_key, revision=None):  # lint-amnesty, pylint: disable=arguments-differ
        """
        Returns True if location exists in this ModuleStore.

        Args:
            revision:
                ModuleStoreEnum.RevisionOption.published_only - checks for the published item only
                ModuleStoreEnum.RevisionOption.draft_only - checks for the draft item only
                None - uses the branch setting, as follows:
                    if branch setting is ModuleStoreEnum.Branch.published_only, checks for the published item only
                    if branch setting is ModuleStoreEnum.Branch.draft_preferred, checks whether draft or published item exists  # lint-amnesty, pylint: disable=line-too-long
        """
        def has_published():
            return super(DraftModuleStore, self).has_item(usage_key)  # lint-amnesty, pylint: disable=super-with-arguments

        def has_draft():
            return super(DraftModuleStore, self).has_item(as_draft(usage_key))  # lint-amnesty, pylint: disable=super-with-arguments

        if revision == ModuleStoreEnum.RevisionOption.draft_only:
            return has_draft()
        elif (
                revision == ModuleStoreEnum.RevisionOption.published_only or
                self.get_branch_setting() == ModuleStoreEnum.Branch.published_only
        ):
            return has_published()
        elif revision is None:
            key = usage_key.to_deprecated_son(prefix='_id.')
            del key['_id.revision']
            return self.collection.count_documents(key) > 0
        else:
            raise UnsupportedRevisionError()

    def delete_course(self, course_key, user_id):  # lint-amnesty, pylint: disable=arguments-differ
        """
        :param course_key: which course to delete
        :param user_id: id of the user deleting the course
        """
        # Note: does not need to inform the bulk mechanism since after the course is deleted,
        # it can't calculate inheritance anyway. Nothing is there to be dirty.
        # delete the assets
        super().delete_course(course_key, user_id)  # lint-amnesty, pylint: disable=super-with-arguments

        # delete all of the db records for the course
        course_query = self._course_key_to_son(course_key)
        self.collection.delete_many(course_query)
        self.delete_all_asset_metadata(course_key, user_id)

        self._emit_course_deleted_signal(course_key)

    def clone_course(self, source_course_id, dest_course_id, user_id, fields=None, **kwargs):
        """
        Only called if cloning within this store or if env doesn't set up mixed.
        * copy the courseware
        """
        # check to see if the source course is actually there
        if not self.has_course(source_course_id):
            raise ItemNotFoundError(f"Cannot find a course at {source_course_id}. Aborting")

        with self.bulk_operations(dest_course_id):
            # verify that the dest_location really is an empty course
            # b/c we don't want the payload, I'm copying the guts of get_items here
            query = self._course_key_to_son(dest_course_id)
            query['_id.category'] = {'$nin': ['course', 'about']}
            if self.collection.count_documents(query, limit=1) > 0:
                raise DuplicateCourseError(
                    dest_course_id,
                    "Course at destination {} is not an empty course. "
                    "You can only clone into an empty course. Aborting...".format(
                        dest_course_id
                    )
                )

            # clone the assets
            super().clone_course(source_course_id, dest_course_id, user_id, fields)  # lint-amnesty, pylint: disable=super-with-arguments

            # get the whole old course
            new_course = self.get_course(dest_course_id)
            if new_course is None:
                # create_course creates the about overview
                new_course = self.create_course(
                    dest_course_id.org, dest_course_id.course, dest_course_id.run, user_id, fields=fields
                )
            else:
                # update fields on existing course
                for key, value in fields.items():
                    setattr(new_course, key, value)
                self.update_item(new_course, user_id)

            # Get all blocks under this namespace which is (tag, org, course) tuple
            blocks = self.get_items(source_course_id, revision=ModuleStoreEnum.RevisionOption.published_only)
            self._clone_blocks(blocks, dest_course_id, user_id)
            course_location = dest_course_id.make_usage_key('course', dest_course_id.run)
            self.publish(course_location, user_id)

            blocks = self.get_items(source_course_id, revision=ModuleStoreEnum.RevisionOption.draft_only)
            self._clone_blocks(blocks, dest_course_id, user_id)

            return True

    def _clone_blocks(self, blocks, dest_course_id, user_id):
        """Clones each block into the given course"""
        for block in blocks:
            original_loc = block.location
            block.location = block.location.map_into_course(dest_course_id)
            if block.location.block_type == 'course':
                block.location = block.location.replace(name=block.location.run)

            log.info("Cloning block %s to %s....", original_loc, block.location)

            if 'data' in block.fields and block.fields['data'].is_set_on(block) and isinstance(block.data, str):  # lint-amnesty, pylint: disable=line-too-long
                block.data = rewrite_nonportable_content_links(
                    original_loc.course_key, dest_course_id, block.data
                )

            # repoint children
            if block.has_children:
                new_children = []
                for child_loc in block.children:
                    child_loc = child_loc.map_into_course(dest_course_id)
                    new_children.append(child_loc)

                block.children = new_children

            self.update_item(block, user_id, allow_not_found=True)

    def _get_raw_parent_locations(self, location, key_revision):
        """
        Get the parents but don't unset the revision in their locations.

        Intended for internal use but not restricted.

        Args:
            location (UsageKey): assumes the location's revision is None; so, uses revision keyword solely
            key_revision:
                MongoRevisionKey.draft - return only the draft parent
                MongoRevisionKey.published - return only the published parent
                ModuleStoreEnum.RevisionOption.all - return both draft and published parents
        """
        _verify_revision_is_published(location)

        # create a query to find all items in the course that have the given location listed as a child
        query = self._course_key_to_son(location.course_key)
        query['definition.children'] = str(location)

        # find all the items that satisfy the query
        parents = self.collection.find(query, {'_id': True}, sort=[SORT_REVISION_FAVOR_DRAFT])

        # return only the parent(s) that satisfy the request
        return [
            BlockUsageLocator._from_deprecated_son(parent['_id'], location.course_key.run)  # lint-amnesty, pylint: disable=protected-access
            for parent in parents
            if (
                # return all versions of the parent if revision is ModuleStoreEnum.RevisionOption.all
                key_revision == ModuleStoreEnum.RevisionOption.all or
                # return this parent if it's direct-only, regardless of which revision is requested
                parent['_id']['category'] in DIRECT_ONLY_CATEGORIES or
                # return this parent only if its revision matches the requested one
                parent['_id']['revision'] == key_revision
            )
        ]

    def get_parent_location(self, location, revision=None, **kwargs):
        '''
        Returns the given location's parent location in this course.

        Returns: version agnostic locations (revision always None) as per the rest of mongo.

        Args:
            revision:
                None - uses the branch setting for the revision
                ModuleStoreEnum.RevisionOption.published_only
                    - return only the PUBLISHED parent if it exists, else returns None
                ModuleStoreEnum.RevisionOption.draft_preferred
                    - return either the DRAFT or PUBLISHED parent, preferring DRAFT, if parent(s) exists,
                        else returns None

                    If the draft has a different parent than the published, it returns only
                    the draft's parent. Because parents don't record their children's revisions, this
                    is actually a potentially fragile deduction based on parent type. If the parent type
                    is not DIRECT_ONLY, then the parent revision must be DRAFT.
                    Only xml_exporter currently uses this argument. Others should avoid it.
        '''
        if revision is None:
            revision = ModuleStoreEnum.RevisionOption.published_only \
                if self.get_branch_setting() == ModuleStoreEnum.Branch.published_only \
                else ModuleStoreEnum.RevisionOption.draft_preferred
        return super().get_parent_location(location, revision, **kwargs)  # lint-amnesty, pylint: disable=super-with-arguments

    def create_xblock(self, runtime, course_key, block_type, block_id=None, fields=None, **kwargs):  # lint-amnesty, pylint: disable=arguments-differ
        """
        Create the new xblock but don't save it. Returns the new block with a draft locator if
        the category allows drafts. If the category does not allow drafts, just creates a published block.

        :param location: a Location--must have a category
        :param definition_data: can be empty. The initial definition_data for the kvs
        :param metadata: can be empty, the initial metadata for the kvs
        :param runtime: if you already have an xmodule from the course, the xmodule.runtime value
        :param fields: a dictionary of field names and values for the new xmodule
        """
        new_block = super().create_xblock(  # lint-amnesty, pylint: disable=super-with-arguments
            runtime, course_key, block_type, block_id, fields, **kwargs
        )
        new_block.location = self.for_branch_setting(new_block.location)
        return wrap_draft(new_block)

    def get_items(self, course_key, revision=None, **kwargs):  # lint-amnesty, pylint: disable=arguments-differ
        """
        Performance Note: This is generally a costly operation, but useful for wildcard searches.

        Returns:
            list of XModuleDescriptor instances for the matching items within the course with
            the given course_key

        NOTE: don't use this to look for courses as the course_key is required. Use get_courses instead.

        Args:
            course_key (CourseKey): the course identifier
            revision:
                ModuleStoreEnum.RevisionOption.published_only - returns only Published items
                ModuleStoreEnum.RevisionOption.draft_only - returns only Draft items
                None - uses the branch setting, as follows:
                    if the branch setting is ModuleStoreEnum.Branch.published_only,
                        returns only Published items
                    if the branch setting is ModuleStoreEnum.Branch.draft_preferred,
                        returns either Draft or Published, preferring Draft items.
        """
        def base_get_items(key_revision):
            return super(DraftModuleStore, self).get_items(course_key, key_revision=key_revision, **kwargs)  # lint-amnesty, pylint: disable=super-with-arguments

        def draft_items():
            return [wrap_draft(item) for item in base_get_items(MongoRevisionKey.draft)]

        def published_items(draft_items):
            # filters out items that are not already in draft_items
            draft_items_locations = {item.location for item in draft_items}
            return [
                item for item in
                base_get_items(MongoRevisionKey.published)
                if item.location not in draft_items_locations
            ]

        if revision == ModuleStoreEnum.RevisionOption.draft_only:
            return draft_items()
        elif revision == ModuleStoreEnum.RevisionOption.published_only \
                or self.get_branch_setting() == ModuleStoreEnum.Branch.published_only:
            return published_items([])
        elif revision is None:
            draft_items = draft_items()
            return draft_items + published_items(draft_items)
        else:
            raise UnsupportedRevisionError()

    def convert_to_draft(self, location, user_id):
        """
        Copy the subtree rooted at source_location and mark the copies as draft.

        Args:
            location: the location of the source (its revision must be None)
            user_id: the ID of the user doing the operation

        Raises:
            InvalidVersionError: if the source can not be made into a draft
            ItemNotFoundError: if the source does not exist
        """
        # TODO (dhm) I don't think this needs to recurse anymore but can convert each unit on demand.
        #     See if that's true.
        # delegating to internal b/c we don't want any public user to use the kwargs on the internal
        self._convert_to_draft(location, user_id, ignore_if_draft=True)

        # return the new draft item (does another fetch)
        # get_item will wrap_draft so don't call it here (otherwise, it would override the is_draft attribute)
        return self.get_item(location)

    def _convert_to_draft(self, location, user_id, delete_published=False, ignore_if_draft=False):  # lint-amnesty, pylint: disable=unused-argument
        """
        Internal method with additional internal parameters to convert a subtree to draft.

        Args:
            location: the location of the source (its revision must be MongoRevisionKey.published)
            user_id: the ID of the user doing the operation
            delete_published (Boolean): intended for use by unpublish
            ignore_if_draft(Boolean): for internal use only as part of depth first change

        Raises:
            InvalidVersionError: if the source can not be made into a draft
            ItemNotFoundError: if the source does not exist
            DuplicateItemError: if the source or any of its descendants already has a draft copy. Only
                useful for unpublish b/c we don't want unpublish to overwrite any existing drafts.
        """
        # verify input conditions: can only convert to draft branch; so, verify that's the setting
        self._verify_branch_setting(ModuleStoreEnum.Branch.draft_preferred)
        _verify_revision_is_published(location)

        # ensure we are not creating a DRAFT of an item that is direct-only
        if location.block_type in DIRECT_ONLY_CATEGORIES:
            raise InvalidVersionError(location)

        def convert_item(item, to_be_deleted):
            """
            Convert the subtree
            """
            # collect the children's ids for future processing
            next_tier = []
            for child in item.get('definition', {}).get('children', []):
                child_loc = BlockUsageLocator.from_string(child)
                next_tier.append(child_loc.to_deprecated_son())

            # insert a new DRAFT version of the item
            item['_id']['revision'] = MongoRevisionKey.draft
            # ensure keys are in fixed and right order before inserting
            item['_id'] = self._id_dict_to_son(item['_id'])
            bulk_record = self._get_bulk_ops_record(location.course_key)
            bulk_record.dirty = True
            try:
                self.collection.insert_one(item)
            except pymongo.errors.DuplicateKeyError:
                # prevent re-creation of DRAFT versions, unless explicitly requested to ignore
                if not ignore_if_draft:
                    raise DuplicateItemError(item['_id'], self, 'collection')  # lint-amnesty, pylint: disable=raise-missing-from

            # delete the old PUBLISHED version if requested
            if delete_published:
                item['_id']['revision'] = MongoRevisionKey.published
                to_be_deleted.append(item['_id'])

            return next_tier

        # convert the subtree using the original item as the root
        self._breadth_first(convert_item, [location])

    def update_item(  # lint-amnesty, pylint: disable=arguments-differ
            self,  # lint-amnesty, pylint: disable=unused-argument
            xblock,
            user_id,
            allow_not_found=False,
            force=False,
            isPublish=False,
            child_update=False,
            **kwargs):
        """
        See superclass doc.
        In addition to the superclass's behavior, this method converts the unit to draft if it's not
        direct-only and not already draft.
        """
        draft_loc = self.for_branch_setting(xblock.location)

        # if the revision is published, defer to base
        if draft_loc.branch == MongoRevisionKey.published:
            item = super().update_item(xblock, user_id, allow_not_found)  # lint-amnesty, pylint: disable=super-with-arguments
            course_key = xblock.location.course_key
            if isPublish or (item.category in DIRECT_ONLY_CATEGORIES and not child_update):
                self._flag_publish_event(course_key)
            return item

        if not super().has_item(draft_loc):  # lint-amnesty, pylint: disable=super-with-arguments
            try:
                # ignore any descendants which are already draft
                self._convert_to_draft(xblock.location, user_id, ignore_if_draft=True)
            except ItemNotFoundError as exception:
                # ignore the exception only if allow_not_found is True and
                # the item that wasn't found is the one that was passed in
                # we make this extra location check so we do not hide errors when converting any children to draft
                if not (allow_not_found and exception.args[0] == xblock.location):
                    raise

        xblock.location = draft_loc
        super().update_item(xblock, user_id, allow_not_found, isPublish=isPublish)  # lint-amnesty, pylint: disable=super-with-arguments
        return wrap_draft(xblock)

    def delete_item(self, location, user_id, revision=None, **kwargs):  # lint-amnesty, pylint: disable=arguments-differ
        """
        Delete an item from this modulestore.
        The method determines which revisions to delete. It disconnects and deletes the subtree.
        In general, it assumes deletes only occur on drafts except for direct_only. The only exceptions
        are internal calls like deleting orphans (during publishing as well as from delete_orphan view).
        To indicate that all versions should be deleted, pass the keyword revision=ModuleStoreEnum.RevisionOption.all.

        * Deleting a DIRECT_ONLY_CATEGORIES block, deletes both draft and published children and removes from parent.
        * Deleting a specific version of block whose parent is of DIRECT_ONLY_CATEGORIES, only removes it from parent if
        the other version of the block does not exist. Deletes only children of same version.
        * Other deletions remove from parent of same version and subtree of same version

        Args:
            location: UsageKey of the item to be deleted
            user_id: id of the user deleting the item
            revision:
                None - deletes the item and its subtree, and updates the parents per description above
                ModuleStoreEnum.RevisionOption.published_only - removes only Published versions
                ModuleStoreEnum.RevisionOption.all - removes both Draft and Published parents
                    currently only provided by contentstore.views.item.orphan_handler
                Otherwise, raises a ValueError.
        """
        self._verify_branch_setting(ModuleStoreEnum.Branch.draft_preferred)
        _verify_revision_is_published(location)

        is_item_direct_only = location.block_type in DIRECT_ONLY_CATEGORIES
        if is_item_direct_only or revision == ModuleStoreEnum.RevisionOption.published_only:
            parent_revision = MongoRevisionKey.published
        elif revision == ModuleStoreEnum.RevisionOption.all:
            parent_revision = ModuleStoreEnum.RevisionOption.all
        else:
            parent_revision = MongoRevisionKey.draft

        # remove subtree from its parent
        parent_locations = self._get_raw_parent_locations(location, key_revision=parent_revision)
        # if no parents, then we're trying to delete something which we should convert to draft
        if not parent_locations:
            # find the published parent, convert it to draft, then manipulate the draft
            parent_locations = self._get_raw_parent_locations(location, key_revision=MongoRevisionKey.published)
            # parent_locations will still be empty if the object was an orphan
            if parent_locations:
                draft_parent = self.convert_to_draft(parent_locations[0], user_id)
                parent_locations = [draft_parent.location]
        # there could be 2 parents if
        #   Case 1: the draft item moved from one parent to another
        # Case 2: revision==ModuleStoreEnum.RevisionOption.all and the single
        # parent has 2 versions: draft and published
        for parent_location in parent_locations:
            # don't remove from direct_only parent if other versions of this still exists (this code
            # assumes that there's only one parent_location in this case)
            if not is_item_direct_only and parent_location.block_type in DIRECT_ONLY_CATEGORIES:
                # see if other version of to-be-deleted root exists
                query = location.to_deprecated_son(prefix='_id.')
                del query['_id.revision']
                if self.collection.count_documents(query) > 1:
                    continue

            parent_block = super().get_item(parent_location)  # lint-amnesty, pylint: disable=super-with-arguments
            parent_block.children.remove(location)
            parent_block.location = parent_location  # ensure the location is with the correct revision
            self.update_item(parent_block, user_id, child_update=True)
        self._flag_publish_event(location.course_key)

        if is_item_direct_only or revision == ModuleStoreEnum.RevisionOption.all:
            as_functions = [as_draft, as_published]
        elif revision == ModuleStoreEnum.RevisionOption.published_only:
            as_functions = [as_published]
        elif revision is None:
            as_functions = [as_draft]
        else:
            raise UnsupportedRevisionError(
                [
                    None,
                    ModuleStoreEnum.RevisionOption.published_only,
                    ModuleStoreEnum.RevisionOption.all
                ]
            )
        self._delete_subtree(location, as_functions)

    def _delete_subtree(self, location, as_functions, draft_only=False):
        """
        Internal method for deleting all of the subtree whose revisions match the as_functions
        """
        course_key = location.course_key

        def _delete_item(current_entry, to_be_deleted):
            """
            Depth first deletion of nodes
            """
            to_be_deleted.append(self._id_dict_to_son(current_entry['_id']))
            next_tier = []
            for child_loc in current_entry.get('definition', {}).get('children', []):
                child_loc = UsageKey.from_string(child_loc).map_into_course(course_key)

                # single parent can have 2 versions: draft and published
                # get draft parents only while deleting draft block
                if draft_only:
                    revision = MongoRevisionKey.draft
                else:
                    revision = ModuleStoreEnum.RevisionOption.all

                parents = self._get_raw_parent_locations(child_loc, revision)
                # Don't delete blocks if one of its parents shouldn't be deleted
                # This should only be an issue for courses have ended up in
                # a state where blocks have multiple parents
                if all(parent.to_deprecated_son() in to_be_deleted for parent in parents):
                    for rev_func in as_functions:
                        current_loc = rev_func(child_loc)
                        current_son = current_loc.to_deprecated_son()
                        next_tier.append(current_son)

            return next_tier

        first_tier = [as_func(location) for as_func in as_functions]
        self._breadth_first(_delete_item, first_tier)

    def _breadth_first(self, function, root_usages):
        """
        Get the root_usage from the db and do a depth first scan. Call the function on each. The
        function should return a list of SON for any next tier items to process and should
        add the SON for any items to delete to the to_be_deleted array.

        At the end, it mass deletes the to_be_deleted items and refreshes the cached metadata inheritance
        tree.

        :param function: a function taking (item, to_be_deleted) and returning [SON] for next_tier invocation
        :param root_usages: the usage keys for the root items (ensure they have the right revision set)
        """
        if len(root_usages) == 0:
            return
        to_be_deleted = []

        def _internal(tier):
            next_tier = []
            tier_items = self.collection.find({'_id': {'$in': tier}})
            for current_entry in tier_items:
                next_tier.extend(function(current_entry, to_be_deleted))

            if len(next_tier) > 0:
                _internal(next_tier)

        _internal([root_usage.to_deprecated_son() for root_usage in root_usages])
        if len(to_be_deleted) > 0:
            bulk_record = self._get_bulk_ops_record(root_usages[0].course_key)
            bulk_record.dirty = True
            self.collection.delete_many({'_id': {'$in': to_be_deleted}})

    def has_changes(self, xblock):
        """
        Check if the subtree rooted at xblock has any drafts and thus may possibly have changes
        :param xblock: xblock to check
        :return: True if there are any drafts anywhere in the subtree under xblock (a weaker
            condition than for other stores)
        """
        return self._cached_has_changes(self.request_cache, xblock)

    @request_cached(
        # use the XBlock's location value in the cache key
        arg_map_function=lambda arg: str(arg.location if isinstance(arg, XBlock) else arg),
        # use this store's request_cache
        request_cache_getter=lambda args, kwargs: args[1],
    )
    def _cached_has_changes(self, request_cache, xblock):  # lint-amnesty, pylint: disable=unused-argument
        """
        Internal has_changes method that caches the result.
        """
        # don't check children if this block has changes (is not public)
        if getattr(xblock, 'is_draft', False):
            return True
        # if this block doesn't have changes, then check its children
        elif xblock.has_children:
            # fix a bug where dangling pointers should imply a change
            if len(xblock.children) > len(xblock.get_children()):
                return True
            return any(self.has_changes(child) for child in xblock.get_children())
        # otherwise there are no changes
        else:
            return False

    def publish(self, location, user_id, **kwargs):  # lint-amnesty, pylint: disable=unused-argument
        """
        Publish the subtree rooted at location to the live course and remove the drafts.
        Such publishing may cause the deletion of previously published but subsequently deleted
        child trees. Overwrites any existing published xblocks from the subtree.

        Treats the publishing of non-draftable items as merely a subtree selection from
        which to descend.

        Raises:
            ItemNotFoundError: if any of the draft subtree nodes aren't found

        Returns:
            The newly published xblock
        """
        # NOTE: cannot easily use self._breadth_first b/c need to get pub'd and draft as pairs
        # (could do it by having 2 breadth first scans, the first to just get all published children
        # and the second to do the publishing on the drafts looking for the published in the cached
        # list of published ones.)
        to_be_deleted = []

        def _internal_depth_first(item_location, is_root):
            """
            Depth first publishing from the given location
            """
            try:
                # handle child does not exist w/o killing publish
                item = self.get_item(item_location)
            except ItemNotFoundError:
                log.warning('Cannot find: %s', item_location)
                return

            # publish the children first
            if item.has_children:
                for child_loc in item.children:
                    _internal_depth_first(child_loc, False)

            if item_location.block_type in DIRECT_ONLY_CATEGORIES or not getattr(item, 'is_draft', False):
                # ignore noop attempt to publish something that can't be or isn't currently draft
                return

            # try to find the originally PUBLISHED version, if it exists
            try:
                original_published = super(DraftModuleStore, self).get_item(item_location)  # lint-amnesty, pylint: disable=super-with-arguments
            except ItemNotFoundError:
                original_published = None

            # if the category of this item allows having children
            if item.has_children:
                if original_published is not None:
                    # see if previously published children were deleted. 2 reasons for children lists to differ:
                    #   Case 1: child deleted
                    #   Case 2: child moved
                    for orig_child in original_published.children:
                        if orig_child not in item.children:
                            published_parent = self.get_parent_location(orig_child)
                            if published_parent == item_location:
                                # Case 1: child was deleted in draft parent item
                                # So, delete published version of the child now that we're publishing the draft parent
                                self._delete_subtree(orig_child, [as_published])
                            else:
                                # Case 2: child was moved to a new draft parent item
                                # So, do not delete the child.  It will be published when the new parent is published.
                                pass

            # update the published (not draft) item (ignoring that item is "draft"). The published
            # may not exist; (if original_published is None); so, allow_not_found
            super(DraftModuleStore, self).update_item(  # lint-amnesty, pylint: disable=super-with-arguments
                item, user_id, isPublish=True, is_publish_root=is_root, allow_not_found=True
            )
            to_be_deleted.append(as_draft(item_location).to_deprecated_son())

        # verify input conditions
        self._verify_branch_setting(ModuleStoreEnum.Branch.draft_preferred)
        _verify_revision_is_published(location)

        _internal_depth_first(location, True)
        course_key = location.course_key
        bulk_record = self._get_bulk_ops_record(course_key)
        if len(to_be_deleted) > 0:
            bulk_record.dirty = True
            self.collection.delete_many({'_id': {'$in': to_be_deleted}})

        self._flag_publish_event(course_key)

        return self.get_item(as_published(location))

    def unpublish(self, location, user_id, **kwargs):  # lint-amnesty, pylint: disable=unused-argument
        """
        Turn the published version into a draft, removing the published version.

        NOTE: unlike publish, this gives an error if called above the draftable level as it's intended
        to remove things from the published version
        """
        # ensure we are not creating a DRAFT of an item that is direct-only
        if location.block_type in DIRECT_ONLY_CATEGORIES:
            raise InvalidVersionError(location)

        self._verify_branch_setting(ModuleStoreEnum.Branch.draft_preferred)
        self._convert_to_draft(location, user_id, delete_published=True)

        course_key = location.course_key
        self._flag_publish_event(course_key)

    def revert_to_published(self, location, user_id=None):
        """
        Reverts an item to its last published version (recursively traversing all of its descendants).
        If no published version exists, an InvalidVersionError is thrown.

        If a published version exists but there is no draft version of this item or any of its descendants, this
        method is a no-op. It is also a no-op if the root item is in DIRECT_ONLY_CATEGORIES.

        :raises InvalidVersionError: if no published version exists for the location specified
        """
        self._verify_branch_setting(ModuleStoreEnum.Branch.draft_preferred)
        _verify_revision_is_published(location)

        if location.block_type in DIRECT_ONLY_CATEGORIES:
            return

        if not self.has_item(location, revision=ModuleStoreEnum.RevisionOption.published_only):
            raise InvalidVersionError(location)

        def delete_draft_only(root_location):
            """
            Helper function that calls delete on the specified location if a draft version of the item exists.
            If no draft exists, this function recursively calls itself on the children of the item.
            """
            query = root_location.to_deprecated_son(prefix='_id.')
            del query['_id.revision']
            versions_found = self.collection.find(
                query, {'_id': True, 'definition.children': True}, sort=[SORT_REVISION_FAVOR_DRAFT]
            )
            versions_found = list(versions_found)
            # If 2 versions versions exist, we can assume one is a published version. Go ahead and do the delete
            # of the draft version.
            if len(versions_found) > 1:
                # Moving a child from published parent creates a draft of the parent and moved child.
                published_version = [
                    version
                    for version in versions_found
                    if version.get('_id').get('revision') != MongoRevisionKey.draft
                ]
                if len(published_version) > 0:
                    # This change makes sure that parents are updated too i.e. an item will have only one parent.
                    self.update_parent_if_moved(root_location, published_version[0], delete_draft_only, user_id)
                self._delete_subtree(root_location, [as_draft], draft_only=True)
            elif len(versions_found) == 1:
                # Since this method cannot be called on something in DIRECT_ONLY_CATEGORIES and we call
                # delete_subtree as soon as we find an item with a draft version, if there is only 1 version
                # it must be published (since adding a child to a published item creates a draft of the parent).
                item = versions_found[0]
                assert item.get('_id').get('revision') != MongoRevisionKey.draft
                for child in item.get('definition', {}).get('children', []):
                    child_loc = BlockUsageLocator.from_string(child)
                    delete_draft_only(child_loc)

        delete_draft_only(location)

    def update_parent_if_moved(self, original_parent_location, published_version, delete_draft_only, user_id):
        """
        Update parent of an item if it has moved.

        Arguments:
            original_parent_location (BlockUsageLocator)  : Original parent block locator.
            published_version (dict)   : Published version of the block.
            delete_draft_only (function)    : A callback function to delete draft children if it was moved.
            user_id (int)   : User id
        """
        for child_location in published_version.get('definition', {}).get('children', []):
            item_location = UsageKey.from_string(child_location).map_into_course(original_parent_location.course_key)
            try:
                source_item = self.get_item(item_location)
            except ItemNotFoundError:
                log.error('Unable to find the item %s', str(item_location))
                return

            if source_item.parent and source_item.parent.block_id != original_parent_location.block_id:
                if self.update_item_parent(item_location, original_parent_location, source_item.parent, user_id):
                    delete_draft_only(BlockUsageLocator.from_string(child_location))

    def _query_children_for_cache_children(self, course_key, items):
        # first get non-draft in a round-trip
        to_process_non_drafts = super()._query_children_for_cache_children(course_key, items)  # lint-amnesty, pylint: disable=super-with-arguments

        to_process_dict = {}
        for non_draft in to_process_non_drafts:
            to_process_dict[BlockUsageLocator._from_deprecated_son(non_draft["_id"], course_key.run)] = non_draft  # lint-amnesty, pylint: disable=protected-access

        if self.get_branch_setting() == ModuleStoreEnum.Branch.draft_preferred:
            # now query all draft content in another round-trip
            query = []
            for item in items:
                item_usage_key = UsageKey.from_string(item).map_into_course(course_key)
                if item_usage_key.block_type not in DIRECT_ONLY_CATEGORIES:
                    query.append(as_draft(item_usage_key).to_deprecated_son())
            if query:
                query = {'_id': {'$in': query}}
                to_process_drafts = list(self.collection.find(query))

                # now we have to go through all drafts and replace the non-draft
                # with the draft. This is because the semantics of the DraftStore is to
                # always return the draft - if available
                for draft in to_process_drafts:
                    draft_loc = BlockUsageLocator._from_deprecated_son(draft["_id"], course_key.run)  # lint-amnesty, pylint: disable=protected-access
                    draft_as_non_draft_loc = as_published(draft_loc)

                    # does non-draft exist in the collection
                    # if so, replace it
                    if draft_as_non_draft_loc in to_process_dict:
                        to_process_dict[draft_as_non_draft_loc] = draft

        # convert the dict - which is used for look ups - back into a list
        queried_children = list(to_process_dict.values())

        return queried_children

    def has_published_version(self, xblock):
        """
        Returns True if this xblock has an existing published version regardless of whether the
        published version is up to date.
        """
        if getattr(xblock, 'is_draft', False):
            published_xblock_location = as_published(xblock.location)
            try:
                xblock.runtime.lookup_item(published_xblock_location)
            except ItemNotFoundError:
                return False
        return True

    def _verify_branch_setting(self, expected_branch_setting):
        """
        Raises an exception if the current branch setting does not match the expected branch setting.
        """
        actual_branch_setting = self.get_branch_setting()
        if actual_branch_setting != expected_branch_setting:
            raise InvalidBranchSetting(
                expected_setting=expected_branch_setting,
                actual_setting=actual_branch_setting
            )


def _verify_revision_is_published(location):
    """
    Asserts that the revision set on the given location is MongoRevisionKey.published
    """
    assert location.branch == MongoRevisionKey.published
