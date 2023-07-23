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
        this.DiscussionUser = (function(_super) {
            __extends(DiscussionUser, _super);

            function DiscussionUser() {
                return DiscussionUser.__super__.constructor.apply(this, arguments);
            }

            DiscussionUser.prototype.following = function(thread) {
                return _.include(this.get('subscribed_thread_ids'), thread.id);
            };

            DiscussionUser.prototype.voted = function(thread) {
                return _.include(this.get('upvoted_ids'), thread.id);
            };

            DiscussionUser.prototype.vote = function(thread) {
                this.get('upvoted_ids').push(thread.id);
                return thread.vote();
            };

            DiscussionUser.prototype.unvote = function(thread) {
                this.set('upvoted_ids', _.without(this.get('upvoted_ids'), thread.id));
                return thread.unvote();
            };

            return DiscussionUser;
        }(Backbone.Model));
    }
}).call(this);
