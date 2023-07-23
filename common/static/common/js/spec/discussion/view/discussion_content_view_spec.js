/* globals DiscussionSpecHelper, DiscussionContentView, Thread */
(function() {
    'use strict';

    describe('DiscussionContentView', function() {
        beforeEach(function() {
            DiscussionSpecHelper.setUpGlobals();
            DiscussionSpecHelper.setUnderscoreFixtures();
            this.threadData = {
                id: '01234567',
                user_id: '567',
                course_id: 'edX/999/test',
                body: 'this is a thread',
                created_at: '2013-04-03T20:08:39Z',
                abuse_flaggers: ['123'],
                votes: {
                    up_count: '42'
                },
                type: 'thread',
                roles: []
            };
            this.thread = new Thread(this.threadData);
            this.view = new DiscussionContentView({
                model: this.thread
            });
            this.view.setElement($('#fixture-element'));
            return this.view.render();
        });

        it('defines the tag', function() {
            expect($('#jasmine-fixtures')).toExist();
            expect(this.view.tagName).toBeDefined();
            return expect(this.view.el.tagName.toLowerCase()).toBe('div');
        });

        it('defines the class', function() {
            return expect(this.view.model).toBeDefined();
        });

        it('is tied to the model', function() {
            return expect(this.view.model).toBeDefined();
        });

        it('can be flagged for abuse', function() {
            this.thread.flagAbuse();
            return expect(this.thread.get('abuse_flaggers')).toEqual(['123', '567']);
        });

        it('can be unflagged for abuse', function() {
            var temp_array;
            temp_array = [];
            temp_array.push(window.user.get('id'));
            this.thread.set('abuse_flaggers', temp_array);
            this.thread.unflagAbuse();
            return expect(this.thread.get('abuse_flaggers')).toEqual([]);
        });
    });
}).call(this);
