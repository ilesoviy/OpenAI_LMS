"""
Testing indexing of blockstore based content libraries
"""
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.test.utils import override_settings
from opaque_keys.edx.locator import LibraryLocatorV2, LibraryUsageLocatorV2
from search.search_engine_base import SearchEngine

from openedx.core.djangoapps.content_libraries.libraries_index import ContentLibraryIndexer, LibraryBlockIndexer
from openedx.core.djangoapps.content_libraries.tests.base import (
    ContentLibrariesRestApiBlockstoreServiceTest,
    ContentLibrariesRestApiTest,
    elasticsearch_test,
)


class ContentLibraryIndexerTestMixin:
    """
    Tests the operation of ContentLibraryIndexer
    """

    @elasticsearch_test
    def setUp(self):
        super().setUp()
        ContentLibraryIndexer.remove_all_items()
        LibraryBlockIndexer.remove_all_items()
        self.searcher = SearchEngine.get_search_engine(ContentLibraryIndexer.INDEX_NAME)

    def test_index_libraries(self):
        """
        Test if libraries are being indexed correctly
        """
        result1 = self._create_library(slug="test-lib-index-1", title="Title 1", description="Description")
        result2 = self._create_library(slug="test-lib-index-2", title="Title 2", description="Description")

        for result in [result1, result2]:
            library_key = LibraryLocatorV2.from_string(result['id'])
            response = ContentLibraryIndexer.get_items([library_key])[0]

            assert response['id'] == result['id']
            assert response['title'] == result['title']
            assert response['description'] == result['description']
            assert response['uuid'] == result['bundle_uuid']
            assert response['num_blocks'] == 0
            assert response['version'] == result['version']
            assert response['last_published'] is None
            assert response['has_unpublished_changes'] is False
            assert response['has_unpublished_deletes'] is False

    def test_schema_updates(self):
        """
        Test that outdated indexes aren't retrieved
        """
        with patch("openedx.core.djangoapps.content_libraries.libraries_index.ContentLibraryIndexer.SCHEMA_VERSION",
                   new=0):
            result = self._create_library(slug="test-lib-schemaupdates-1", title="Title 1", description="Description")
            library_key = LibraryLocatorV2.from_string(result['id'])
            assert len(ContentLibraryIndexer.get_items([library_key])) == 1

        with patch("openedx.core.djangoapps.content_libraries.libraries_index.ContentLibraryIndexer.SCHEMA_VERSION",
                   new=1):
            assert len(ContentLibraryIndexer.get_items([library_key])) == 0

            call_command("reindex_content_library", all=True, force=True)

            assert len(ContentLibraryIndexer.get_items([library_key])) == 1

    def test_remove_all_libraries(self):
        """
        Test if remove_all_items() deletes all libraries
        """
        lib1 = self._create_library(slug="test-lib-rm-all-1", title="Title 1", description="Description")
        lib2 = self._create_library(slug="test-lib-rm-all-2", title="Title 2", description="Description")
        library_key1 = LibraryLocatorV2.from_string(lib1['id'])
        library_key2 = LibraryLocatorV2.from_string(lib2['id'])

        assert len(ContentLibraryIndexer.get_items([library_key1, library_key2])) == 2

        ContentLibraryIndexer.remove_all_items()
        assert len(ContentLibraryIndexer.get_items()) == 0

    def test_update_libraries(self):
        """
        Test if indexes are updated when libraries are updated
        """
        lib = self._create_library(slug="test-lib-update", title="Title", description="Description")
        library_key = LibraryLocatorV2.from_string(lib['id'])

        self._update_library(lib['id'], title="New Title", description="New Title")

        response = ContentLibraryIndexer.get_items([library_key])[0]

        assert response['id'] == lib['id']
        assert response['title'] == 'New Title'
        assert response['description'] == 'New Title'
        assert response['uuid'] == lib['bundle_uuid']
        assert response['num_blocks'] == 0
        assert response['version'] == lib['version']
        assert response['last_published'] is None
        assert response['has_unpublished_changes'] is False
        assert response['has_unpublished_deletes'] is False

        self._delete_library(lib['id'])
        assert ContentLibraryIndexer.get_items([library_key]) == []
        ContentLibraryIndexer.get_items([library_key])

    def test_update_library_blocks(self):
        """
        Test if indexes are updated when blocks in libraries are updated
        """
        def commit_library_and_verify(library_key):
            """
            Commit library changes, and verify that there are no uncommited changes anymore
            """
            last_published = ContentLibraryIndexer.get_items([library_key])[0]['last_published']
            self._commit_library_changes(str(library_key))
            response = ContentLibraryIndexer.get_items([library_key])[0]
            assert response['has_unpublished_changes'] is False
            assert response['has_unpublished_deletes'] is False
            assert response['last_published'] >= last_published
            return response

        def verify_uncommitted_libraries(library_key, has_unpublished_changes, has_unpublished_deletes):
            """
            Verify uncommitted changes and deletes in the index
            """
            response = ContentLibraryIndexer.get_items([library_key])[0]
            assert response['has_unpublished_changes'] == has_unpublished_changes
            assert response['has_unpublished_deletes'] == has_unpublished_deletes
            return response

        lib = self._create_library(slug="test-lib-update-block", title="Title", description="Description")
        library_key = LibraryLocatorV2.from_string(lib['id'])

        # Verify uncommitted new blocks
        block = self._add_block_to_library(lib['id'], "problem", "problem1")
        response = verify_uncommitted_libraries(library_key, True, False)
        assert response['last_published'] is None
        assert response['num_blocks'] == 1
        # Verify committed new blocks
        self._commit_library_changes(lib['id'])
        response = verify_uncommitted_libraries(library_key, False, False)
        assert response['num_blocks'] == 1
        # Verify uncommitted deleted blocks
        self._delete_library_block(block['id'])
        response = verify_uncommitted_libraries(library_key, True, True)
        assert response['num_blocks'] == 0
        # Verify committed deleted blocks
        self._commit_library_changes(lib['id'])
        response = verify_uncommitted_libraries(library_key, False, False)
        assert response['num_blocks'] == 0

        block = self._add_block_to_library(lib['id'], "problem", "problem1")
        self._commit_library_changes(lib['id'])

        # Verify changes to blocks
        # Verify OLX updates on blocks
        self._set_library_block_olx(block["id"], "<problem/>")
        verify_uncommitted_libraries(library_key, True, False)
        commit_library_and_verify(library_key)
        # Verify asset updates on blocks
        self._set_library_block_asset(block["id"], "whatever.png", b"data")
        verify_uncommitted_libraries(library_key, True, False)
        commit_library_and_verify(library_key)
        self._delete_library_block_asset(block["id"], "whatever.png", expect_response=204)
        verify_uncommitted_libraries(library_key, True, False)
        commit_library_and_verify(library_key)

        lib2 = self._create_library(slug="test-lib-update-block-2", title="Title 2", description="Description")
        self._add_block_to_library(lib2["id"], "problem", "problem1")
        self._commit_library_changes(lib2["id"])

        #Verify new links on libraries
        self._link_to_library(lib["id"], "library_2", lib2["id"])
        verify_uncommitted_libraries(library_key, True, False)
        #Verify reverting uncommitted changes
        self._revert_library_changes(lib["id"])
        verify_uncommitted_libraries(library_key, False, False)


@override_settings(FEATURES={**settings.FEATURES, 'ENABLE_CONTENT_LIBRARY_INDEX': True})
@elasticsearch_test
class ContentLibraryIndexerBlockstoreServiceTest(
    ContentLibraryIndexerTestMixin,
    ContentLibrariesRestApiBlockstoreServiceTest,
):
    """
    Tests the operation of ContentLibraryIndexer using the standalone Blockstore service.
    """


@override_settings(FEATURES={**settings.FEATURES, 'ENABLE_CONTENT_LIBRARY_INDEX': True})
@elasticsearch_test
class ContentLibraryIndexerTest(
    ContentLibraryIndexerTestMixin,
    ContentLibrariesRestApiTest,
):
    """
    Tests the operation of ContentLibraryIndexer using the installed Blockstore app.
    """


class LibraryBlockIndexerTestMixin:
    """
    Tests the operation of LibraryBlockIndexer
    """

    @elasticsearch_test
    def setUp(self):
        super().setUp()
        ContentLibraryIndexer.remove_all_items()
        LibraryBlockIndexer.remove_all_items()
        self.searcher = SearchEngine.get_search_engine(LibraryBlockIndexer.INDEX_NAME)

    def test_index_block(self):
        """
        Test if libraries are being indexed correctly
        """
        lib = self._create_library(slug="test-lib-index-1", title="Title 1", description="Description")
        block1 = self._add_block_to_library(lib['id'], "problem", "problem1")
        block2 = self._add_block_to_library(lib['id'], "problem", "problem2")

        assert len(LibraryBlockIndexer.get_items()) == 2

        for block in [block1, block2]:
            usage_key = LibraryUsageLocatorV2.from_string(block['id'])
            response = LibraryBlockIndexer.get_items([usage_key])[0]

            assert response['id'] == block['id']
            assert response['def_key'] == block['def_key']
            assert response['block_type'] == block['block_type']
            assert response['display_name'] == block['display_name']
            assert response['has_unpublished_changes'] == block['has_unpublished_changes']

    def test_schema_updates(self):
        """
        Test that outdated indexes aren't retrieved
        """
        lib = self._create_library(slug="test-lib--block-schemaupdates-1", title="Title 1", description="Description")
        with patch("openedx.core.djangoapps.content_libraries.libraries_index.LibraryBlockIndexer.SCHEMA_VERSION",
                   new=0):
            block = self._add_block_to_library(lib['id'], "problem", "problem1")
            assert len(LibraryBlockIndexer.get_items([block['id']])) == 1

        with patch("openedx.core.djangoapps.content_libraries.libraries_index.LibraryBlockIndexer.SCHEMA_VERSION",
                   new=1):
            assert len(LibraryBlockIndexer.get_items([block['id']])) == 0

            call_command("reindex_content_library", all=True, force=True)

            assert len(LibraryBlockIndexer.get_items([block['id']])) == 1

    def test_remove_all_items(self):
        """
        Test if remove_all_items() deletes all libraries
        """
        lib1 = self._create_library(slug="test-lib-rm-all", title="Title 1", description="Description")
        self._add_block_to_library(lib1['id'], "problem", "problem1")
        self._add_block_to_library(lib1['id'], "problem", "problem2")
        assert len(LibraryBlockIndexer.get_items()) == 2

        LibraryBlockIndexer.remove_all_items()
        assert len(LibraryBlockIndexer.get_items()) == 0

    def test_crud_block(self):
        """
        Test that CRUD operations on blocks are reflected in the index
        """
        lib = self._create_library(slug="test-lib-crud-block", title="Title", description="Description")
        block = self._add_block_to_library(lib['id'], "problem", "problem1")

        # Update OLX, verify updates in index
        self._set_library_block_olx(block["id"], '<problem display_name="new_name"/>')
        response = LibraryBlockIndexer.get_items([block['id']])[0]
        assert response['display_name'] == 'new_name'
        assert response['has_unpublished_changes'] is True

        # Verify has_unpublished_changes after committing library
        self._commit_library_changes(lib['id'])
        response = LibraryBlockIndexer.get_items([block['id']])[0]
        assert response['has_unpublished_changes'] is False

        # Verify has_unpublished_changes after reverting library
        self._set_library_block_asset(block["id"], "whatever.png", b"data")
        response = LibraryBlockIndexer.get_items([block['id']])[0]
        assert response['has_unpublished_changes'] is True

        self._revert_library_changes(lib['id'])
        response = LibraryBlockIndexer.get_items([block['id']])[0]
        assert response['has_unpublished_changes'] is False

        # Verify that deleting block removes it from index
        self._delete_library_block(block['id'])
        assert LibraryBlockIndexer.get_items([block['id']]) == []

        # Verify that deleting a library removes its blocks from index too
        self._add_block_to_library(lib['id'], "problem", "problem1")
        LibraryBlockIndexer.get_items([block['id']])
        self._delete_library(lib['id'])
        assert LibraryBlockIndexer.get_items([block['id']]) == []


@override_settings(FEATURES={**settings.FEATURES, 'ENABLE_CONTENT_LIBRARY_INDEX': True})
@elasticsearch_test
class LibraryBlockIndexerBlockstoreServiceTest(
    LibraryBlockIndexerTestMixin,
    ContentLibrariesRestApiBlockstoreServiceTest,
):
    """
    Tests the operation of LibraryBlockIndexer using the standalone Blockstore service.
    """


@override_settings(FEATURES={**settings.FEATURES, 'ENABLE_CONTENT_LIBRARY_INDEX': True})
@elasticsearch_test
class LibraryBlockIndexerTest(
    LibraryBlockIndexerTestMixin,
    ContentLibrariesRestApiTest,
):
    """
    Tests the operation of LibraryBlockIndexer using the installed Blockstore app.
    """
