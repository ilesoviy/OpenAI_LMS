define(['jquery', 'logger', 'js/courseware/toggle_element_visibility', 'moment'],
    function($, Logger, ToggleElementVisibility, moment) {
        'use strict';

        describe('show/hide with mouse click', function() {
            beforeEach(function() {
                loadFixtures('js/fixtures/courseware/course_updates.html');
                ToggleElementVisibility();
                spyOn(Logger, 'log');
            });

            it('ensures update will hide on hide button click', function() {
                var $shownUpdate = $('.toggle-visibility-element:not(.hidden)').first(),
                    $updateButton = $shownUpdate.siblings('.toggle-visibility-button');
                $updateButton.trigger('click');
                expect($shownUpdate).toHaveClass('hidden');
                expect($updateButton.text()).toEqual('Show');
            });

            it('ensures update will show on show button click', function() {
                var $hiddenUpdate = $('.toggle-visibility-element.hidden').first(),
                    $updateButton = $hiddenUpdate.siblings('.toggle-visibility-button');
                $updateButton.trigger('click');
                expect($hiddenUpdate).not.toHaveClass('hidden');
                expect($updateButton.text()).toEqual('Hide');
            });

            it('ensures old updates will show on button click', function() {
                // on page load old updates will be hidden
                var $oldUpdates = $('.toggle-visibility-element.old-updates');
                expect($oldUpdates).toHaveClass('hidden');

                // on click on show earlier update button old updates will be shown
                $('.toggle-visibility-button.show-older-updates').trigger('click');
                expect($oldUpdates).not.toHaveClass('hidden');
            });

            it('sends a tracking event on hide and show', function() {
                var $update = $('.toggle-visibility-element:not(.hidden)').first();
                $update.siblings('.toggle-visibility-button').trigger('click');
                expect(Logger.log).toHaveBeenCalledWith('edx.course.home.course_update.toggled', {
                    action: 'hide',
                    publish_date: moment('December 1, 2015', 'MMM DD, YYYY').format()
                });
            });
        });
    });
