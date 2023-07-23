/* globals Backbone, _ */

(function() {
    'use strict';

    if (Backbone) {
        this.DiscussionTopicMenuView = Backbone.View.extend({
            events: {
                'change .post-topic': 'handleTopicEvent'
            },

            attributes: {
                class: 'post-field'
            },

            initialize: function(options) {
                this.course_settings = options.course_settings;
                this.currentTopicId = options.topicId;
                this.group_name = options.group_name;
                _.bindAll(this,
                    'handleTopicEvent'
                );
                return this;
            },

            render: function() {
                var $general,
                    context = _.clone(this.course_settings.attributes);

                context.topics_html = this.renderCategoryMap(this.course_settings.get('category_map'));
                edx.HtmlUtils.setHtml(this.$el, edx.HtmlUtils.template($('#topic-template').html())(context));

                $general = this.$('.post-topic option:contains(General)'); // always return array.

                if (this.getCurrentTopicId()) {
                    this.setTopic(this.$('.post-topic option').filter(
                        '[data-discussion-id="' + this.getCurrentTopicId() + '"]'
                    ));
                } else if ($general.length > 0) {
                    this.setTopic($general.first());
                } else {
                    this.setTopic(this.$('.post-topic option').first());
                }
                return this.$el;
            },

            renderCategoryMap: function(map) {
                var categoryTemplate = edx.HtmlUtils.template($('#new-post-menu-category-template').html()),
                    entryTemplate = edx.HtmlUtils.template($('#new-post-menu-entry-template').html()),
                    mappedCategorySnippets = _.map(map.children, function(child) {
                        var entry,
                            html = '',
                            name = child[0], // child[0] is the category name
                            type = child[1]; // child[1] is the type (i.e. 'entry' or 'subcategory')
                        if (_.has(map.entries, name) && type === 'entry') {
                            entry = map.entries[name];
                            html = entryTemplate({
                                text: name,
                                id: entry.id,
                                is_divided: entry.is_divided
                            });
                        } else { // subcategory
                            html = categoryTemplate({
                                text: name,
                                entries: this.renderCategoryMap(map.subcategories[name])
                            });
                        }
                        return html;
                    }, this);

                return edx.HtmlUtils.joinHtml.apply(null, mappedCategorySnippets);
            },

            handleTopicEvent: function(event) {
                this.setTopic($('option:selected', event.target));
                return this;
            },

            setTopic: function($target) {
                if ($target.data('discussion-id')) {
                    this.topicText = this.getFullTopicName($target);
                    this.currentTopicId = $target.data('discussion-id');
                    $target.prop('selected', true);
                    this.trigger('thread:topic_change', $target);
                }
                return this;
            },

            getCurrentTopicId: function() {
                return this.currentTopicId;
            },

            /**
             * Return full name for the `topicElement` if it is passed.
             * Otherwise, full name for the current topic will be returned.
             * @param {jQuery Element} [topicElement]
             * @return {String}
             */
            getFullTopicName: function(topicElement) {
                var name;
                if (topicElement) {
                    name = topicElement.html();
                    _.each(topicElement.parents('optgroup'), function(item) {
                        name = $(item).attr('label') + ' / ' + name;
                    });
                    return name;
                } else {
                    return this.topicText;
                }
            }
        });
    }
}).call(this);
