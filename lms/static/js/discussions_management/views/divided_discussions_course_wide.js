(function(define) {
    'use strict';

    define(['jquery', 'underscore', 'backbone', 'gettext', 'js/discussions_management/views/divided_discussions',
        'edx-ui-toolkit/js/utils/html-utils'],
    function($, _, Backbone, gettext, DividedDiscussionConfigurationView, HtmlUtils) {
        var CourseWideDiscussionsView = DividedDiscussionConfigurationView.extend({
            events: {
                'change .check-discussion-subcategory-course-wide': 'discussionCategoryStateChanged',
                'click .cohort-course-wide-discussions-form .action-save': 'saveCourseWideDiscussionsForm'
            },

            initialize: function(options) {
                this.template = HtmlUtils.template($('#divided-discussions-course-wide-tpl').text());
                this.discussionSettings = options.discussionSettings;
            },

            render: function() {
                HtmlUtils.setHtml(this.$('.course-wide-discussions-nav'), this.template({
                    courseWideTopicsHtml: this.getCourseWideDiscussionsHtml(
                        this.model.get('course_wide_discussions')
                    )
                }));
                this.setDisabled(this.$('.cohort-course-wide-discussions-form .action-save'), true);
            },

            /**
                     * Returns the html list for course-wide discussion topics.
                     * @param {object} courseWideDiscussions - course-wide discussions object from server.
                     * @returns {HtmlSnippet} - HTML list for course-wide discussion topics.
                     */
            getCourseWideDiscussionsHtml: function(courseWideDiscussions) {
                var subCategoryTemplate = HtmlUtils.template($('#cohort-discussions-subcategory-tpl').html()),
                    entries = courseWideDiscussions.entries,
                    children = courseWideDiscussions.children;

                return HtmlUtils.joinHtml.apply(this, _.map(children, function(child) {
                    // child[0] is the category name, child[1] is the type.
                    // For course wide discussions, the type is always 'entry'
                    var name = child[0],
                        entry = entries[name];
                    return subCategoryTemplate({
                        name: name,
                        id: entry.id,
                        is_divided: entry.is_divided,
                        type: 'course-wide'
                    });
                }));
            },

            /**
                     * Enables the save button for course-wide discussions.
                     */
            discussionCategoryStateChanged: function(event) {
                event.preventDefault();
                this.setDisabled(this.$('.cohort-course-wide-discussions-form .action-save'), false);
            },

            /**
                     * Sends the courseWideDividedDiscussions to the server and renders the view.
                     */
            saveCourseWideDiscussionsForm: function(event) {
                var self = this,
                    courseWideDividedDiscussions = self.getDividedDiscussions(
                        '.check-discussion-subcategory-course-wide:checked'
                    ),
                    fieldData = {divided_course_wide_discussions: courseWideDividedDiscussions};

                event.preventDefault();

                self.saveForm(self.$('.course-wide-discussion-topics'), fieldData)
                    .done(function() {
                        self.model.fetch()
                            .done(function() {
                                self.render();
                                self.showMessage(gettext('Your changes have been saved.'),
                                    self.$('.course-wide-discussion-topics')
                                );
                            }).fail(function() {
                                var errorMessage = gettext("We've encountered an error. Refresh your browser and then try again."); // eslint-disable-line max-len
                                self.showMessage(errorMessage, self.$('.course-wide-discussion-topics'), 'error');
                            });
                    });
            }

        });
        return CourseWideDiscussionsView;
    });
}).call(this, define || RequireJS.define);
