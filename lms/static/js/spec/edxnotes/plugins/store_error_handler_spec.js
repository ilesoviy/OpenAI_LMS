define([
    'jquery', 'underscore', 'annotator_1.2.9',
    'edx-ui-toolkit/js/utils/spec-helpers/ajax-helpers',
    'js/spec/edxnotes/helpers',
    'js/edxnotes/views/notes_factory',
    'js/edxnotes/utils/notes_collector'
], function($, _, Annotator, AjaxHelpers, Helpers, NotesFactory, NotesCollector) {
    'use strict';

    describe('Store Error Handler Custom Message', function() {
        beforeEach(function() {
            spyOn(Annotator, 'showNotification');
            loadFixtures('js/fixtures/edxnotes/edxnotes_wrapper.html');
            NotesCollector.cleanup();
        });

        afterEach(function() {
            while (Annotator._instances.length > 0) { // eslint-disable-line no-underscore-dangle
                Annotator._instances[0].destroy(); // eslint-disable-line no-underscore-dangle
            }
        });

        it('can handle custom error if sent from server', function() {
            var requests = AjaxHelpers.requests(this);
            var token = Helpers.makeToken();
            _.each($('.edx-notes-wrapper'), function(wrapper) {
                NotesFactory.factory(wrapper, {
                    endpoint: '/test_endpoint',
                    user: 'a user',
                    usageId: 'an usage',
                    courseId: 'a course',
                    token: token,
                    tokenUrl: '/test_token_url'
                });
            });

            var errorMsg = 'can\'t create more notes';
            AjaxHelpers.respondWithError(requests, 400, {error_msg: errorMsg});
            expect(Annotator.showNotification).toHaveBeenCalledWith(errorMsg, Annotator.Notification.ERROR);
        });
    });
});
