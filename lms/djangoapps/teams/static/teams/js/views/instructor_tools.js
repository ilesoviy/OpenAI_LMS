(function(define) {
    'use strict';

    define(['backbone',
        'underscore',
        'gettext',
        'edx-ui-toolkit/js/utils/string-utils',
        'teams/js/views/team_utils',
        'common/js/components/utils/view_utils',
        'text!teams/templates/instructor-tools.underscore',
        'edx-ui-toolkit/js/utils/html-utils'],
    function(Backbone, _, gettext, StringUtils, TeamUtils, ViewUtils, instructorToolbarTemplate, HtmlUtils) {
        return Backbone.View.extend({

            events: {
                'click .action-delete': 'deleteTeam',
                'click .action-edit-members': 'editMembership'
            },

            initialize: function(options) {
                this.team = options.team;
                this.teamEvents = options.teamEvents;
            },

            render: function() {
                HtmlUtils.setHtml(this.$el, HtmlUtils.template(instructorToolbarTemplate)({}));
                return this;
            },

            deleteTeam: function(event) {
                event.preventDefault();
                ViewUtils.confirmThenRunOperation(
                    gettext('Delete this team?'),
                    gettext('Deleting a team is permanent and cannot be undone.'
                            + 'All members are removed from the team, and team discussions can no longer be accessed.'),
                    gettext('Delete'),
                    _.bind(this.handleDelete, this)
                );
            },

            editMembership: function(event) {
                event.preventDefault();
                Backbone.history.navigate(
                    'teams/' + this.team.get('topic_id') + '/' + this.team.id + '/edit-team/manage-members',
                    {trigger: true}
                );
            },

            handleDelete: function() {
                var self = this,
                    postDelete = function() {
                        self.teamEvents.trigger('teams:update', {
                            action: 'delete',
                            team: self.team
                        });
                        Backbone.history.navigate('topics/' + self.team.get('topic_id'), {trigger: true});
                        TeamUtils.showMessage(
                            StringUtils.interpolate(
                                gettext('Team "{team}" successfully deleted.'),
                                {team: self.team.get('name')},
                                true
                            ),
                            'success'
                        );
                    };
                this.team.destroy().then(postDelete).fail(function(response) {
                    // In the 404 case, this team has already been
                    // deleted by someone else. Since the team was
                    // successfully deleted anyway, just show a
                    // success message.
                    if (response.status === 404) {
                        postDelete();
                    }
                });
            }
        });
    });
}).call(this, define || RequireJS.define);
