/* globals DiscussionUtil */
(function() {
    'use strict';

    var __hasProp = {}.hasOwnProperty,
        __extends = function(child, parent) {
            for (var key in parent) {
                if (__hasProp.call(parent, key)) {
                    child[key] = parent[key];
                }
            }
            function ctor() {
                this.constructor = child;
            }

            ctor.prototype = parent.prototype;
            child.prototype = new ctor();
            child.__super__ = parent.prototype;
            return child;
        };

    if (typeof Backbone !== 'undefined' && Backbone !== null) {
        this.ResponseCommentEditView = (function(_super) {
            __extends(ResponseCommentEditView, _super);

            function ResponseCommentEditView(options) {
                this.options = options;
                return ResponseCommentEditView.__super__.constructor.apply(this, arguments);
            }

            ResponseCommentEditView.prototype.events = {
                'click .post-update': 'update',
                'click .post-cancel': 'cancel_edit'
            };

            ResponseCommentEditView.prototype.$ = function(selector) {
                return this.$el.find(selector);
            };

            ResponseCommentEditView.prototype.initialize = function() {
                return ResponseCommentEditView.__super__.initialize.call(this);
            };

            ResponseCommentEditView.prototype.render = function() {
                var context = $.extend({mode: this.options.mode, startHeader: this.options.startHeader},
                    this.model.attributes);
                this.template = edx.HtmlUtils.template($('#response-comment-edit-template').html());
                edx.HtmlUtils.setHtml(
                    this.$el,
                    this.template(context)
                );
                this.delegateEvents();
                DiscussionUtil.makeWmdEditor(this.$el, $.proxy(this.$, this), 'edit-comment-body');
                return this;
            };

            ResponseCommentEditView.prototype.update = function(event) {
                return this.trigger('comment:update', event);
            };

            ResponseCommentEditView.prototype.cancel_edit = function(event) {
                return this.trigger('comment:cancel_edit', event);
            };

            return ResponseCommentEditView;
        }(Backbone.View));
    }
}).call(window);
