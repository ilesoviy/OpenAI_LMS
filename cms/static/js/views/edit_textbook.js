define(['js/views/baseview', 'underscore', 'jquery', 'js/views/edit_chapter', 'common/js/components/views/feedback_notification'],
    function(BaseView, _, $, EditChapterView, NotificationView) {
        var EditTextbook = BaseView.extend({
            initialize: function() {
                this.template = this.loadTemplate('edit-textbook');
                this.listenTo(this.model, 'invalid', this.render);
                var chapters = this.model.get('chapters');
                this.listenTo(chapters, 'add', this.addOne);
                this.listenTo(chapters, 'reset', this.addAll);
            },
            tagName: 'section',
            className: 'textbook',
            render: function() {
                this.$el.html(this.template({ // xss-lint: disable=javascript-jquery-html
                    name: this.model.get('name'),
                    error: this.model.validationError
                }));
                this.addAll();
                return this;
            },
            events: {
                'change input[name=textbook-name]': 'setName',
                submit: 'setAndClose',
                'click .action-cancel': 'cancel',
                'click .action-add-chapter': 'createChapter'
            },
            addOne: function(chapter) {
                var view = new EditChapterView({model: chapter});
                this.$('ol.chapters').append(view.render().el);
                return this;
            },
            addAll: function() {
                this.model.get('chapters').each(this.addOne, this);
            },
            createChapter: function(e) {
                if (e && e.preventDefault) { e.preventDefault(); }
                this.setValues();
                this.model.get('chapters').add([{}]);
            },
            setName: function(e) {
                if (e && e.preventDefault) { e.preventDefault(); }
                this.model.set('name', this.$('#textbook-name-input').val(), {silent: true});
            },
            setValues: function() {
                this.setName();
                var that = this;
                _.each(this.$('li'), function(li, i) {
                    var chapter = that.model.get('chapters').at(i);
                    if (!chapter) { return; }
                    chapter.set({
                        name: $('.chapter-name', li).val(),
                        asset_path: $('.chapter-asset-path', li).val()
                    });
                });
                return this;
            },
            setAndClose: function(e) {
                if (e && e.preventDefault) { e.preventDefault(); }
                this.setValues();
                if (!this.model.isValid()) { return; }
                var saving = new NotificationView.Mini({
                    title: gettext('Saving')
                }).show();
                var that = this;
                this.model.save({}, {
                    success: function() {
                        that.model.setOriginalAttributes();
                        that.close();
                    },
                    complete: function() {
                        saving.hide();
                    }
                });
            },
            cancel: function(e) {
                if (e && e.preventDefault) { e.preventDefault(); }
                this.model.reset();
                return this.close();
            },
            close: function() {
                var textbooks = this.model.collection;
                this.remove();
                if (this.model.isNew()) {
                // if the textbook has never been saved, remove it
                    textbooks.remove(this.model);
                }
                // don't forget to tell the model that it's no longer being edited
                this.model.set('editing', false);
                return this;
            }
        });
        return EditTextbook;
    });
