/* globals Sequence */
(function() {
    'use strict';

    describe('Sequence', function() {
        var local = {},
            keydownHandler,
            keys = {
                ENTER: 13,
                LEFT: 37,
                RIGHT: 39
            };

        beforeEach(function() {
            var runtime = jasmine.createSpyObj('TestRuntime', ['handlerUrl']);
            loadFixtures('sequence.html');
            local.XBlock = window.XBlock = jasmine.createSpyObj('XBlock', ['initializeBlocks']);
            this.sequence = new Sequence($('.xblock-student_view-sequential'), runtime);
        });

        afterEach(function() {
            delete local.XBlock;
        });

        keydownHandler = function(key) {
            var event = document.createEvent('Event');
            event.keyCode = key;
            event.initEvent('keydown', false, false);
            document.dispatchEvent(event);
        };

        describe('Navbar', function() {
            it('works with keyboard navigation LEFT and ENTER', function() {
                this.sequence.$('.nav-item[data-index=0]').focus();
                keydownHandler(keys.LEFT);
                keydownHandler(keys.ENTER);

                expect(this.sequence.$('.nav-item[data-index=1]')).toHaveAttr({
                    'aria-expanded': 'false',
                    'aria-selected': 'false',
                    tabindex: '-1'
                });
                expect(this.sequence.$('.nav-item[data-index=0]')).toHaveAttr({
                    'aria-expanded': 'true',
                    'aria-selected': 'true',
                    tabindex: '0'
                });
            });

            it('works with keyboard navigation RIGHT and ENTER', function() {
                this.sequence.$('.nav-item[data-index=0]').focus();
                keydownHandler(keys.RIGHT);
                keydownHandler(keys.ENTER);

                expect(this.sequence.$('.nav-item[data-index=0]')).toHaveAttr({
                    'aria-expanded': 'false',
                    'aria-selected': 'false',
                    tabindex: '-1'
                });
                expect(this.sequence.$('.nav-item[data-index=1]')).toHaveAttr({
                    'aria-expanded': 'true',
                    'aria-selected': 'true',
                    tabindex: '0'
                });
            });

            it('Completion Indicator missing', function() {
                this.sequence.$('.nav-item[data-index=0]').children('.check-circle').remove();
                spyOn($, 'postWithPrefix').and.callFake(function(url, data, callback) {
                    callback({
                        complete: true
                    });
                });
                this.sequence.update_completion(1);
                expect($.postWithPrefix).not.toHaveBeenCalled();
            });

            describe('Completion', function() {
                beforeEach(function() {
                    expect(
                        this.sequence.$('.nav-item[data-index=0]').children('.check-circle').first()
                            .hasClass('is-hidden')
                    ).toBe(true);
                    expect(
                        this.sequence.$('.nav-item[data-index=1]').children('.check-circle').first()
                            .hasClass('is-hidden')
                    ).toBe(true);
                });

                afterEach(function() {
                    expect($.postWithPrefix).toHaveBeenCalled();
                    expect(
                        this.sequence.$('.nav-item[data-index=1]').children('.check-circle').first()
                            .hasClass('is-hidden')
                    ).toBe(true);
                });

                it('API check returned true', function() {
                    spyOn($, 'postWithPrefix').and.callFake(function(url, data, callback) {
                        callback({
                            complete: true
                        });
                    });
                    this.sequence.update_completion(1);
                    expect(
                        this.sequence.$('.nav-item[data-index=0]').children('.check-circle').first()
                            .hasClass('is-hidden')
                    ).toBe(false);
                });

                it('API check returned false', function() {
                    spyOn($, 'postWithPrefix').and.callFake(function(url, data, callback) {
                        callback({
                            complete: false
                        });
                    });
                    this.sequence.update_completion(1);
                    expect(
                        this.sequence.$('.nav-item[data-index=0]').children('.check-circle').first()
                            .hasClass('is-hidden')
                    ).toBe(true);
                });
            });
        });
    });
}).call(this);
