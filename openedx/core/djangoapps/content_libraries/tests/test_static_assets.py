"""
Tests for static asset files in Blockstore-based Content Libraries
"""


import requests

from openedx.core.djangoapps.content_libraries.tests.base import (
    ContentLibrariesRestApiBlockstoreServiceTest,
    ContentLibrariesRestApiTest,
)

# Binary data representing an SVG image file
SVG_DATA = """<svg xmlns="http://www.w3.org/2000/svg" height="30" width="100">
  <text x="0" y="15" fill="red">SVG is 🔥</text>
</svg>""".encode()

# part of an .srt transcript file
TRANSCRIPT_DATA = b"""1
00:00:00,260 --> 00:00:01,510
Welcome to edX.

2
00:00:01,510 --> 00:00:04,480
I'm Anant Agarwal, I'm the president of edX,
"""


class ContentLibrariesStaticAssetsTestMixin:
    """
    Tests for static asset files in Blockstore-based Content Libraries

    WARNING: every test should have a unique library slug, because even though
    the django/mysql database gets reset for each test case, the lookup between
    library slug and bundle UUID does not because it's assumed to be immutable
    and cached forever.
    """

    def test_asset_crud(self):
        """
        Test create, read, update, and write of a static asset file.

        Also tests that the static asset file (an image in this case) can be
        used in an HTML block.
        """
        library = self._create_library(slug="asset-lib1", title="Static Assets Test Library")
        block = self._add_block_to_library(library["id"], "html", "html1")
        block_id = block["id"]
        file_name = "image.svg"

        # A new block has no assets:
        assert self._get_library_block_assets(block_id) == []
        self._get_library_block_asset(block_id, file_name, expect_response=404)

        # Upload an asset file
        self._set_library_block_asset(block_id, file_name, SVG_DATA)

        # Get metadata about the uploaded asset file
        metadata = self._get_library_block_asset(block_id, file_name)
        assert metadata['path'] == file_name
        assert metadata['size'] == len(SVG_DATA)
        asset_list = self._get_library_block_assets(block_id)
        # We don't just assert that 'asset_list == [metadata]' because that may
        # break in the future if the "get asset" view returns more detail than
        # the "list assets" view.
        assert len(asset_list) == 1
        assert asset_list[0]['path'] == metadata['path']
        assert asset_list[0]['size'] == metadata['size']
        assert asset_list[0]['url'] == metadata['url']

        # Download the file and check that it matches what was uploaded.
        # We need to download using requests since this is served by Blockstore,
        # which the django test client can't interact with.
        content_get_result = requests.get(metadata["url"])
        assert content_get_result.content == SVG_DATA

        # Set some OLX referencing this asset:
        self._set_library_block_olx(block_id, """
            <html display_name="HTML with Image"><![CDATA[
                <img src="/static/image.svg" alt="An image that says 'SVG is lit' using a fire emoji" />
            ]]></html>
        """)
        # Publish the OLX and the new image file, since published data gets
        # served differently by Blockstore and we should test that too.
        self._commit_library_changes(library["id"])
        metadata = self._get_library_block_asset(block_id, file_name)
        assert metadata['path'] == file_name
        assert metadata['size'] == len(SVG_DATA)
        # Download the file from the new URL:
        content_get_result = requests.get(metadata["url"])
        assert content_get_result.content == SVG_DATA

        # Check that the URL in the student_view gets rewritten:
        fragment = self._render_block_view(block_id, "student_view")
        assert '/static/image.svg' not in fragment['content']
        assert metadata['url'] in fragment['content']

    def test_asset_filenames(self):
        """
        Test various allowed and disallowed filenames
        """
        library = self._create_library(slug="asset-lib2", title="Static Assets Test Library")
        block = self._add_block_to_library(library["id"], "html", "html1")
        block_id = block["id"]
        file_size = len(SVG_DATA)

        # Unicode names are allowed
        file_name = "🏕.svg"  # (camping).svg
        self._set_library_block_asset(block_id, file_name, SVG_DATA)
        assert self._get_library_block_asset(block_id, file_name)['path'] == file_name
        assert self._get_library_block_asset(block_id, file_name)['size'] == file_size

        # Subfolder names are allowed
        file_name = "transcripts/en.srt"
        self._set_library_block_asset(block_id, file_name, SVG_DATA)
        assert self._get_library_block_asset(block_id, file_name)['path'] == file_name
        assert self._get_library_block_asset(block_id, file_name)['size'] == file_size

        # '../' is definitely not allowed
        file_name = "../definition.xml"
        self._set_library_block_asset(block_id, file_name, SVG_DATA, expect_response=400)

        # 'a////////b' is not allowed
        file_name = "a////////b"
        self._set_library_block_asset(block_id, file_name, SVG_DATA, expect_response=400)

    def test_video_transcripts(self):
        """
        Test that video blocks can read transcript files out of blockstore.
        """
        library = self._create_library(slug="transcript-test-lib", title="Transcripts Test Library")
        block = self._add_block_to_library(library["id"], "video", "video1")
        block_id = block["id"]
        self._set_library_block_olx(block_id, """
            <video
                youtube_id_1_0="3_yD_cEKoCk"
                display_name="Welcome Video with Transcript"
                download_track="true"
                transcripts='{"en": "3_yD_cEKoCk-en.srt"}'
            />
        """)
        # Upload the transcript file
        self._set_library_block_asset(block_id, "3_yD_cEKoCk-en.srt", TRANSCRIPT_DATA)

        transcript_handler_url = self._get_block_handler_url(block_id, "transcript")

        def check_sjson():
            """
            Call the handler endpoint which the video player uses to load the transcript as SJSON
            """
            url = transcript_handler_url + 'translation/en'
            response = self.client.get(url)
            assert response.status_code == 200
            assert 'Welcome to edX' in response.content.decode('utf-8')

        def check_download():
            """
            Call the handler endpoint which the video player uses to download the transcript SRT file
            """
            url = transcript_handler_url + 'download'
            response = self.client.get(url)
            assert response.status_code == 200
            assert response.content == TRANSCRIPT_DATA

        check_sjson()
        check_download()
        # Publish the OLX and the transcript file, since published data gets
        # served differently by Blockstore and we should test that too.
        self._commit_library_changes(library["id"])
        check_sjson()
        check_download()


class ContentLibrariesStaticAssetsBlockstoreServiceTest(
    ContentLibrariesStaticAssetsTestMixin,
    ContentLibrariesRestApiBlockstoreServiceTest,
):
    """
    Tests for static asset files in Blockstore-based Content Libraries, using the standalone Blockstore service.
    """


class ContentLibrariesStaticAssetsTest(
    ContentLibrariesStaticAssetsTestMixin,
    ContentLibrariesRestApiTest,
):
    """
    Tests for static asset files in Blockstore-based Content Libraries, using the installed Blockstore app.
    """
