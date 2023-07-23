define(['backbone', 'URI', 'underscore', 'edx-ui-toolkit/js/utils/spec-helpers/ajax-helpers',
    'teams/js/spec_helpers/team_spec_helpers'],
function(Backbone, URI, _, AjaxHelpers, TeamSpecHelpers) {
    'use strict';

    describe('TopicCollection', function() {
        var topicCollection, testRequestParam;
        beforeEach(function() {
            topicCollection = TeamSpecHelpers.createMockTopicCollection();
        });

        testRequestParam = function(self, param, value) {
            var requests = AjaxHelpers.requests(self),
                request,
                url,
                params;
            topicCollection.fetch();
            request = AjaxHelpers.currentRequest(requests);
            url = new URI(request.url);
            params = url.query(true);
            expect(params[param]).toBe(value);
        };

        it('sets its page size based on initial page size', function() {
            expect(topicCollection.getPageSize()).toBe(5);
            expect(topicCollection.getTotalPages()).toBe(2);
        });

        it('sorts by name', function() {
            testRequestParam(this, 'order_by', 'name');
        });

        it('passes a course_id to the server', function() {
            testRequestParam(this, 'course_id', TeamSpecHelpers.testCourseID);
        });

        it('URL encodes its course_id ', function() {
            topicCollection.course_id = 'my+course+id';
            testRequestParam(this, 'course_id', 'my+course+id');
        });

        it('sets itself to stale on receiving a teams create or delete event', function() {
            expect(topicCollection.isStale).toBe(false);
            TeamSpecHelpers.triggerTeamEvent('create');
            expect(topicCollection.isStale).toBe(true);
            topicCollection.isStale = false;
            TeamSpecHelpers.triggerTeamEvent('delete');
            expect(topicCollection.isStale).toBe(true);
        });
    });
});
