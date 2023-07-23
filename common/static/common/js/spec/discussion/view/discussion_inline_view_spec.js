/* globals
 _, Discussion, DiscussionCourseSettings, DiscussionViewSpecHelper, DiscussionSpecHelper,
 DiscussionInlineView, DiscussionUtil, DiscussionThreadShowView, Thread
 */
(function() {
    'use strict';

    describe('DiscussionInlineView', function() {
        var createTestView, showDiscussion, setNextAjaxResult,
            TEST_THREAD_TITLE = 'Test thread title';

        beforeEach(function() {
            DiscussionSpecHelper.setUpGlobals();
            setFixtures(
                '<div class="discussion-module" data-discussion-id="test-discussion-id"'
                + '  data-user-create-comment="true"'
                + '  data-user-create-subcomment="true"'
                + '  data-read-only="false">'
                + '  <div class="discussion-module-header">'
                + '    <h3 class="discussion-module-title">Test Discussion</h3>'
                + '    <div class="inline-discussion-topic">'
                + '      <span class="inline-discussion-topic-title">Topic:</span> Category / Target '
                + '    </div>'
                + '  </div>'
                + '  <button class="discussion-show btn btn-brand" data-discussion-id="test-discussion-id">'
                + '     <span class="button-text">Show Discussion</span>'
                + '  </button>'
                + '</div>'
            );
            DiscussionSpecHelper.setUnderscoreFixtures();
            this.ajaxSpy = spyOn($, 'ajax');

            // Don't attempt to render markdown
            spyOn(DiscussionUtil, 'makeWmdEditor');
            spyOn(DiscussionThreadShowView.prototype, 'convertMath');
        });

        createTestView = function(test) {
            var testView;
            var courseSettings = DiscussionSpecHelper.createTestCourseSettings({
                groups: [
                    {
                        id: 1,
                        name: 'Cohort1'
                    }, {
                        id: 2,
                        name: 'Cohort2'
                    }
                ]
            });
            setNextAjaxResult(test, {
                user_info: DiscussionSpecHelper.getTestUserInfo(),
                roles: DiscussionSpecHelper.getTestRoleInfo(),
                course_settings: courseSettings.attributes,
                discussion_data: DiscussionViewSpecHelper.makeThreadWithProps({
                    commentable_id: 'test-topic',
                    title: TEST_THREAD_TITLE
                }),
                page: 1,
                num_pages: 1,
                content: {
                    endorsed_responses: [],
                    non_endorsed_responses: [],
                    children: []
                }
            });
            testView = new DiscussionInlineView({
                el: $('.discussion-module')
            });
            testView.render();
            return testView;
        };

        showDiscussion = function(test, testView) {
            var courseSettings = DiscussionSpecHelper.createTestCourseSettings({
                groups: [
                    {
                        id: 1,
                        name: 'Cohort1'
                    }, {
                        id: 2,
                        name: 'Cohort2'
                    }
                ]
            });
            setNextAjaxResult(test, {
                user_info: DiscussionSpecHelper.getTestUserInfo(),
                roles: DiscussionSpecHelper.getTestRoleInfo(),
                course_settings: courseSettings.attributes,
                discussion_data: DiscussionViewSpecHelper.makeThreadWithProps({
                    commentable_id: 'test-topic',
                    title: TEST_THREAD_TITLE
                }),
                page: 1,
                num_pages: 1,
                content: {
                    endorsed_responses: [],
                    non_endorsed_responses: [],
                    children: []
                }
            });
            testView.$('.discussion-show').click();
        };

        setNextAjaxResult = function(test, result) {
            test.ajaxSpy.and.callFake(function(params) {
                var deferred = $.Deferred();
                deferred.resolve();
                params.success(result);
                return deferred;
            });
        };

        describe('inline discussion', function() {
            it('is shown by default', function() {
                var testView = createTestView(this),
                    showButton = testView.$('.discussion-show');

                // Verify that the discussion is shown without clicking anything
                expect(showButton).toHaveClass('shown');
                expect(showButton.text().trim()).toEqual('Hide Discussion');
                expect(testView.$('.inline-discussion:visible')).not.toHaveClass('is-hidden');
            });
            it('is shown after "Show Discussion" is clicked while discussions are hidden', function() {
                var testView = createTestView(this),
                    showButton = testView.$('.discussion-show');

                // hide the discussion; discussions are loaded by default
                testView.$('.discussion-show').click();
                showDiscussion(this, testView);

                // Verify that the discussion is now shown again
                expect(showButton).toHaveClass('shown');
                expect(showButton.text().trim()).toEqual('Hide Discussion');
                expect(testView.$('.inline-discussion:visible')).not.toHaveClass('is-hidden');
            });

            it('is hidden after "Hide Discussion" is clicked', function() {
                var testView = createTestView(this),
                    showButton = testView.$('.discussion-show');

                // Hide the discussion by clicking the toggle button
                testView.$('.discussion-show').click();

                // Verify that the discussion is now hidden
                expect(showButton).not.toHaveClass('shown');
                expect(showButton.text().trim()).toEqual('Show Discussion');
                expect(testView.$('.inline-discussion:visible')).toHaveClass('is-hidden');
            });
        });

        describe('new post form', function() {
            it('should not be visible when the discussion is first shown', function() {
                var testView = createTestView(this);
                showDiscussion(this, testView);
                expect(testView.$('.new-post-article')).toHaveClass('is-hidden');
            });

            it('should be shown when the "Add a Post" button is clicked', function() {
                var testView = createTestView(this);
                showDiscussion(this, testView);
                testView.$('.new-post-btn').click();
                expect(testView.$('.new-post-article')).not.toHaveClass('is-hidden');
            });

            it('should be hidden when the "Cancel" button is clicked', function() {
                var testView = createTestView(this);
                showDiscussion(this, testView);
                testView.$('.new-post-btn').click();
                testView.$('.forum-new-post-form .cancel').click();
                expect(testView.$('.new-post-article')).toHaveClass('is-hidden');
            });

            it('should be hidden when the "Close" button is clicked', function() {
                var testView = createTestView(this);
                showDiscussion(this, testView);
                testView.$('.new-post-btn').click();
                testView.$('.forum-new-post-form .add-post-cancel').click();
                expect(testView.$('.new-post-article')).toHaveClass('is-hidden');
            });

            it('should return to the thread listing after adding a post', function() {
                var testView = createTestView(this);
                showDiscussion(this, testView);

                // Navigate to an individual thread
                testView.$('.forum-nav-thread-link').click();

                // Click "Add a Post", fill in the form, and submit it
                testView.$('.new-post-btn').click();
                testView.$('.js-post-title').text('Test title');
                testView.$('.wmd-input').text('Test body');
                setNextAjaxResult(this, {
                    hello: 'world'
                });
                testView.$('.forum-new-post-form .submit').click();

                // Verify that the list of threads is shown
                expect(testView.$('.inline-threads')).not.toHaveClass('is-hidden');

                // Verify that the individual thread is no longer shown
                expect(testView.$('.group-visibility-label').length).toBe(0);
            });
        });

        describe('thread listing', function() {
            it('builds a view that lists the threads', function() {
                var testView = createTestView(this);
                showDiscussion(this, testView);
                expect(testView.$('.forum-nav-thread-title').text()).toBe(TEST_THREAD_TITLE);
            });
        });

        describe('thread post drill down', function() {
            it('can drill down to a thread', function() {
                var testView = createTestView(this);
                showDiscussion(this, testView);
                testView.$('.forum-nav-thread-link').click();

                // Verify that the list of threads is hidden
                expect(testView.$('.inline-threads')).toHaveClass('is-hidden');

                // Verify that the individual thread is shown
                expect(testView.$('.group-visibility-label').text().trim()).toBe('This post is visible to everyone.');
            });

            it('can go back to the list of threads', function() {
                var testView = createTestView(this);
                showDiscussion(this, testView);
                testView.$('.forum-nav-thread-link').click();
                testView.$('.all-posts-btn').click();

                // Verify that the list of threads is shown
                expect(testView.$('.inline-threads')).not.toHaveClass('is-hidden');

                // Verify that the individual thread is no longer shown
                expect(testView.$('.group-visibility-label').length).toBe(0);
            });

            it('marks a thread as read once it is opened', function() {
                var testView = createTestView(this);
                var thread;
                showDiscussion(this, testView);
                thread = testView.$('.forum-nav-thread');

                // The thread is marked as unread.
                expect(thread).toHaveClass('never-read');

                // Navigate to the thread.
                thread.find('.forum-nav-thread-link').click();

                // The thread is no longer marked as unread.
                expect(thread).not.toHaveClass('never-read');
            });
        });
    });
}());
