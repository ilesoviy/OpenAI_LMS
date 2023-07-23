/* globals Discussion, DiscussionCourseSettings, DiscussionUser, DiscussionUtil */
(function(define) {
    'use strict';

    define(
        [
            'underscore',
            'jquery',
            'edx-ui-toolkit/js/utils/constants',
            'common/js/discussion/discussion',
            'common/js/spec_helpers/discussion_spec_helper',
            'discussion/js/views/discussion_board_view'
        ],
        function(_, $, constants, Discussion, DiscussionSpecHelper, DiscussionBoardView) {
            describe('DiscussionBoardView', function() {
                var createDiscussionBoardView;
                createDiscussionBoardView = function() {
                    var discussionBoardView,
                        discussion = DiscussionSpecHelper.createTestDiscussion({}),
                        courseSettings = DiscussionSpecHelper.createTestCourseSettings();

                    setFixtures('<div class="discussion-board"><div class="forum-search"></div></div>');
                    DiscussionSpecHelper.setUnderscoreFixtures();

                    discussionBoardView = new DiscussionBoardView({
                        el: $('.discussion-board'),
                        discussion: discussion,
                        courseSettings: courseSettings
                    });
                    window.ENABLE_FORUM_DAILY_DIGEST = true;
                    window.user = new DiscussionUser({
                        id: 99
                    });

                    return discussionBoardView;
                };

                describe('goHome view', function() {
                    it('Ensure no ajax request when digests are unavailable', function() {
                        var discussionBoardView = createDiscussionBoardView();
                        spyOn(DiscussionUtil, 'safeAjax').and.callThrough();
                        window.ENABLE_FORUM_DAILY_DIGEST = false;

                        discussionBoardView.goHome();
                        expect(DiscussionUtil.safeAjax).not.toHaveBeenCalled();
                    });
                    it('Verify the ajax request when digests are available', function() {
                        var discussionBoardView = createDiscussionBoardView();
                        discussionBoardView.render();
                        spyOn(DiscussionUtil, 'safeAjax').and.callThrough();

                        discussionBoardView.goHome();
                        expect(DiscussionUtil.safeAjax).toHaveBeenCalled();
                    });
                });

                describe('Thread List View', function() {
                    it('should ensure the mode is all', function() {
                        var discussionBoardView = createDiscussionBoardView().render(),
                            threadListView = discussionBoardView.discussionThreadListView;
                        expect(threadListView.mode).toBe('all');
                    });
                });

                describe('Search events', function() {
                    it('perform search when enter pressed inside search textfield', function() {
                        var discussionBoardView = createDiscussionBoardView(),
                            threadListView;
                        discussionBoardView.render();
                        threadListView = discussionBoardView.discussionThreadListView;
                        spyOn(threadListView, 'performSearch');
                        discussionBoardView.$('.search-input').trigger($.Event('keydown', {
                            which: constants.keyCodes.enter
                        }));
                        expect(threadListView.performSearch).toHaveBeenCalled();
                    });

                    it('perform search when search icon is clicked', function() {
                        var discussionBoardView = createDiscussionBoardView(),
                            threadListView;
                        discussionBoardView.render();
                        threadListView = discussionBoardView.discussionThreadListView;
                        spyOn(threadListView, 'performSearch');
                        discussionBoardView.$el.find('.search-button').click();
                        expect(threadListView.performSearch).toHaveBeenCalled();
                    });
                });
            });
        });
}).call(this, define || RequireJS.define);
