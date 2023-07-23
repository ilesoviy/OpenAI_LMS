(function() {
    'use strict';

    describe('VideoPlaySkipControl', function() {
        var state, oldOTBD;

        beforeEach(function() {
            oldOTBD = window.onTouchBasedDevice;
            window.onTouchBasedDevice = jasmine
                .createSpy('onTouchBasedDevice').and.returnValue(null);
            state = jasmine.initializePlayer('video_with_bumper.html');
            $('.poster .btn-play').click();
            spyOn(state.bumperState.videoCommands, 'execute');
        });

        afterEach(function() {
            $('source').remove();
            state.storage.clear();
            if (state.bumperState && state.bumperState.videoPlayer) {
                state.bumperState.videoPlayer.destroy();
            }
            window.onTouchBasedDevice = oldOTBD;
            if (state.videoPlayer) {
                _.result(state.videoPlayer, 'destroy');
            }
        });

        it('can render the control', function() {
            expect($('.video_control.play')).toBeInDOM();
        });

        it('can update state on play', function() {
            state.el.trigger('play');
            expect($('.video_control.play')).not.toBeInDOM();
            expect($('.video_control.skip')).toBeInDOM();
        });

        it('can start video playing on click', function() {
            $('.video_control.play').click();
            expect(state.bumperState.videoCommands.execute).toHaveBeenCalledWith('play');
        });

        it('can skip the video on click', function() {
            state.el.trigger('play');
            spyOn(state.bumperState.videoPlayer, 'isPlaying').and.returnValue(true);
            $('.video_control.skip').first().click();
            expect(state.bumperState.videoCommands.execute).toHaveBeenCalledWith('skip');
        });

        it('can destroy itself', function() {
            var plugin = state.bumperState.videoPlaySkipControl,
                el = plugin.el;
            spyOn($.fn, 'off').and.callThrough();
            plugin.destroy();
            expect(state.bumperState.videoPlaySkipControl).toBeUndefined();
            expect(el).not.toBeInDOM();
            expect($.fn.off).toHaveBeenCalledWith('destroy', plugin.destroy);
        });
    });
}).call(this);
