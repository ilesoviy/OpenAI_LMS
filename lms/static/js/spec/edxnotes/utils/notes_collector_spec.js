define([
    'jquery', 'underscore', 'annotator_1.2.9', 'edx-ui-toolkit/js/utils/spec-helpers/ajax-helpers',
    'js/edxnotes/views/notes_factory', 'js/edxnotes/utils/notes_collector', 'js/spec/edxnotes/helpers'
], function(
    $, _, Annotator, AjaxHelpers, NotesFactory, NotesCollector, Helpers
) {
    'use strict';

    describe('EdxNotes NotesCollector', function() {
        beforeEach(function() {
            loadFixtures('js/fixtures/edxnotes/edxnotes_wrapper.html');
            NotesCollector.cleanup();
        });

        afterEach(function() {
            while (Annotator._instances.length > 0) { // eslint-disable-line no-underscore-dangle
                Annotator._instances[0].destroy(); // eslint-disable-line no-underscore-dangle
            }
            NotesCollector.cleanup();
        });

        it('sends single search request to fetch notes for all HTML components', function() {
            var requests = AjaxHelpers.requests(this),
                token = Helpers.makeToken();

            _.each($('.edx-notes-wrapper'), function(wrapper, index) {
                NotesFactory.factory(wrapper, {
                    endpoint: '/test_endpoint/',
                    user: 'a user',
                    usageId: 'usage ' + index,
                    courseId: 'a course',
                    token: token,
                    tokenUrl: '/test_token_url'
                });
            });

            expect(requests.length).toBe(1);
            AjaxHelpers.expectJsonRequest(requests, 'GET',
                '/test_endpoint/search/?usage_id=usage%200&usage_id=usage%201&user=a+user&course_id=a+course'
            );
        });
    });
});
