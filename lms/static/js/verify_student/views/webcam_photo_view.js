/**
 * Interface for retrieving webcam photos.
 * Supports HTML5 and Flash.
 */
var edx = edx || {},
    key = {
        enter: 13
    };

(function($, _, Backbone, gettext) {
    'use strict';

    edx.verify_student = edx.verify_student || {};

    edx.verify_student.WebcamPhotoView = Backbone.View.extend({

        template: '#webcam_photo-tpl',
        el: '#webcam',

        backends: {
            html5: {
                name: 'html5',

                initialize: function(obj) {
                    this.URL = (window.URL || window.webkitURL);
                    this.video = obj.video || '';
                    this.canvas = obj.canvas || '';
                    this.stream = null;

                    // Start the capture
                    var getUserMedia = this.getUserMediaFunc();
                    if (getUserMedia) {
                        getUserMedia(
                            {
                                video: true,

                                // Specify the `fake` constraint if we detect we are running in a test
                                // environment. In Chrome, this will do nothing, but in Firefox, it will
                                // instruct the browser to use a fake video device.
                                fake: window.location.hostname === 'localhost'
                            },
                            _.bind(this.getUserMediaCallback, this),
                            _.bind(this.handleVideoFailure, this)
                        );
                    }
                },

                isSupported: function() {
                    return this.getUserMediaFunc() !== undefined;
                },

                snapshot: function() {
                    var video, canvas, aspectRatio;

                    if (this.stream) {
                        video = this.getVideo();
                        canvas = this.getCanvas();
                        // keep canvas aspect ratio same as video while drawing image.
                        aspectRatio = canvas.width / video.videoWidth;
                        canvas.width = video.videoWidth * aspectRatio;
                        canvas.height = video.videoHeight * aspectRatio;
                        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
                        video.pause();
                        return true;
                    }

                    return false;
                },

                getImageData: function() {
                    return this.getCanvas().toDataURL('image/png');
                },

                reset: function() {
                    this.getVideo().play();
                },

                getUserMediaFunc: function() {
                    var userMedia = (
                        navigator.getUserMedia || navigator.webkitGetUserMedia
                        || navigator.mozGetUserMedia || navigator.msGetUserMedia
                    );

                    if (userMedia) {
                        return _.bind(userMedia, navigator);
                    }
                },

                getUserMediaCallback: function(stream) {
                    var video = this.getVideo();
                    this.stream = stream;
                    video.srcObject = stream;
                    video.play();
                    this.trigger('webcam-loaded');
                },

                getVideo: function() {
                    return $(this.video).first()[0];
                },

                getCanvas: function() {
                    return $(this.canvas).first()[0];
                },

                handleVideoFailure: function() {
                    this.trigger(
                        'error',
                        gettext('Video Capture Error'),
                        gettext('Please verify that your webcam is connected and that you have allowed your browser to access it.')
                    );
                }
            },

            flash: {

                name: 'flash',

                initialize: function(obj) {
                    this.wrapper = obj.wrapper || '';
                    this.imageData = '';

                    // Wait for the player to load, then verify camera support
                    // Trigger an error if no camera is available.
                    this.checkCameraSupported();
                },

                isSupported: function() {
                    try {
                        var flashObj = new ActiveXObject('ShockwaveFlash.ShockwaveFlash');
                        if (flashObj) {
                            return true;
                        }
                    } catch (ex) {
                        if (navigator.mimeTypes['application/x-shockwave-flash'] !== undefined) {
                            return true;
                        }
                    }

                    return false;
                },

                snapshot: function() {
                    var flashObj = this.getFlashObject();
                    if (flashObj.cameraAuthorized()) {
                        this.imageData = flashObj.snap();
                        return true;
                    }
                    return false;
                },

                reset: function() {
                    this.getFlashObject().reset();
                },

                getImageData: function() {
                    return this.imageData;
                },

                getFlashObject: function() {
                    return $('#flash_video')[0];
                },

                checkCameraSupported: function() {
                    var flashObj = this.getFlashObject(),
                        isLoaded = false,
                        hasCamera = false;

                    isLoaded = (
                        flashObj
                        && flashObj.hasOwnProperty('percentLoaded')
                        && flashObj.percentLoaded() === 100
                    );

                    // On some browsers, the flash object will say it has a camera
                    // even "percentLoaded" isn't defined.
                    hasCamera = (
                        flashObj
                        && flashObj.hasOwnProperty('hasCamera')
                        && flashObj.hasCamera()
                    );

                    // If we've fully loaded, and no camera is available,
                    // then show an error.
                    if (isLoaded && !hasCamera) {
                        this.trigger(
                            'error',
                            gettext('No Webcam Detected'),
                            gettext("You don't seem to have a webcam connected.") + '  '
                            + gettext('Double-check that your webcam is connected and working to continue.')
                        );
                    // eslint-disable-next-line brace-style
                    }

                    // If we're still waiting for the player to load, check
                    // back later.
                    else if (!isLoaded && !hasCamera) {
                        setTimeout(_.bind(this.checkCameraSupported, this), 50);
                    }

                    // Otherwise, the flash player says it has a camera,
                    // so we don't need to keep checking.
                }
            }
        },

        initialize: function(obj) {
            this.submitButton = obj.submitButton || '';
            this.modelAttribute = obj.modelAttribute || '';
            this.errorModel = obj.errorModel || null;
            this.backend = this.backends[obj.backendName] || obj.backend;
            this.captureSoundPath = obj.captureSoundPath || '';

            _.extend(this.backend, Backbone.Events);
            this.backend.initialize({
                wrapper: '#camera',
                video: '#photo_id_video',
                canvas: '#photo_id_canvas'
            });

            this.listenTo(this.backend, 'error', this.handleError);
            this.listenTo(this.backend, 'webcam-loaded', this.handleWebcamLoaded);
        },

        isSupported: function() {
            return this.backend.isSupported();
        },

        render: function() {
            var renderedHtml,
                $resetBtn,
                $captureBtn;

            // Set the submit button to disabled by default
            this.setSubmitButtonEnabled(false);

            // Load the template for the webcam into the DOM
            renderedHtml = edx.HtmlUtils.template($(this.template).html())(
                {backendName: this.backend.name}
            );
            edx.HtmlUtils.setHtml($(this.el), renderedHtml);

            $resetBtn = this.$el.find('#webcam_reset_button');
            $captureBtn = this.$el.find('#webcam_capture_button');

            // Install event handlers
            $resetBtn.on('click', _.bind(this.reset, this));
            $captureBtn.on('click', _.bind(this.capture, this));

            $resetBtn.on('keyup', _.bind(this.resetByEnter, this));

            // Show the capture button
            $captureBtn.removeClass('is-hidden');
            $('#webcam_capture_button', this.el).removeClass('is-hidden');
            $('#webcam_capture_sound', this.el).attr('src', this.captureSoundPath);

            return this;
        },

        reset: function() {
            // Disable the submit button
            this.setSubmitButtonEnabled(false);

            // Reset the video capture
            this.backend.reset();

            // Reset data on the model
            this.model.set(this.modelAttribute, '');

            // Go back to the initial button state
            $('#webcam_reset_button', this.el).addClass('is-hidden');
            $('#webcam_capture_button', this.el).removeClass('is-hidden');
            $(this.submitButton).attr('title', '');
        },

        resetByEnter: function(event) {
            if (event.keyCode == key.enter) {
                this.reset();
            }
        },
        capture: function() {
            // Take a snapshot of the video
            var success = this.backend.snapshot();

            if (success) {
                // Trigger an event which parent views can use to fire a
                // business intelligence event
                this.trigger('imageCaptured');

                // Hide the capture button, and show the reset button
                $('#webcam_capture_button', this.el).addClass('is-hidden');
                $('#webcam_reset_button', this.el).removeClass('is-hidden');

                // Save the data to the model
                this.model.set(this.modelAttribute, this.backend.getImageData());

                // Enable the submit button
                this.setSubmitButtonEnabled(true);
                this.setSubmitButtonFocused();
                this.captureSound();
            }
        },

        handleWebcamLoaded: function(errorTitle, errorMsg) {
            // Hide the text behind camera
            $('#camera .placeholder-art', this.el).hide();
        },

        handleError: function(errorTitle, errorMsg) {
            // Hide the buttons
            $('#webcam_capture_button', this.el).addClass('is-hidden');
            $('#webcam_reset_button', this.el).addClass('is-hidden');

            // Show the error message
            if (this.errorModel) {
                this.errorModel.set({
                    errorTitle: errorTitle,
                    errorMsg: errorMsg,
                    shown: true
                });
            }
        },

        setSubmitButtonEnabled: function(isEnabled) {
            $(this.submitButton)
                .toggleClass('is-disabled', !isEnabled)
                .prop('disabled', !isEnabled)
                .attr('aria-disabled', !isEnabled);
        },

        captureSound: function() {
            $('#webcam_capture_sound')[0].play();
        },

        setSubmitButtonFocused: function() {
            $(this.submitButton)
                .trigger('focus')
                .attr('title', gettext('Photo Captured successfully.'));
        },

        isMobileDevice: function() {
            // Check whether user is using mobile device or not
            return (!!navigator.userAgent.match(/(Android|iPad|iPhone|iPod)/g));
        }
    });

    /**
     * Retrieve a supported webcam view implementation.
     *
     * The priority order from most to least preferable is:
     * 1) HTML5
     * 2) Flash
     * 3) File input
     *
     * @param  {Object} obj Parameters to the webcam view.
     * @return {Object}     A Backbone view.
     */
    edx.verify_student.getSupportedWebcamView = function(obj) {
        var view = null;

        // First choice is HTML5, supported by most web browsers
        obj.backendName = 'html5';
        view = new edx.verify_student.WebcamPhotoView(obj);
        if (view.isSupported()) {
            return view;
        }

        // Second choice is Flash, required for older versions of IE
        obj.backendName = 'flash';
        view = new edx.verify_student.WebcamPhotoView(obj);
        if (view.isSupported()) {
            return view;
        }
        // If user is not using mobile device and Flash is not available
        // then show user error message for Flash
        if (!view.isMobileDevice() && !view.isSupported()) {
            view.backend.trigger(
                'error',
                gettext('No Flash Detected'),
                gettext("You don't seem to have Flash installed. Get Flash to continue your verification.")
            );
            return view;
        }

        // Last resort is HTML file input with image capture.
        // This will work everywhere, and on iOS it will
        // allow users to take a photo with the camera.
        return new edx.verify_student.ImageInputView(obj);
    };
}(jQuery, _, Backbone, gettext));
