(function(define) {
    'use strict';

    define(['jquery', 'jquery.cookie'], function($) {
        var EnrollmentInterface = {

            urls: {
                baskets: '/api/commerce/v0/baskets/'
            },

            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },

            /**
             * Enroll a user in a course, then redirect the user.
             * @param  {string} courseKey  Slash-separated course key.
             * @param  {string} redirectUrl The URL to redirect to once enrollment completes.
             */
            enroll: function(courseKey, redirectUrl) {
                var data_obj = {course_id: courseKey},
                    data = JSON.stringify(data_obj);

                $.ajax({
                    url: this.urls.baskets,
                    type: 'POST',
                    contentType: 'application/json; charset=utf-8',
                    data: data,
                    headers: this.headers,
                    context: this
                }).fail(function(jqXHR) {
                    var responseData = JSON.parse(jqXHR.responseText);
                    if (jqXHR.status === 403 && responseData.user_message_url) {
                        // Check if we've been blocked from the course
                        // because of country access rules.
                        // If so, redirect to a page explaining to the user
                        // why they were blocked.
                        this.redirect(responseData.user_message_url);
                    } else {
                        // Otherwise, redirect the user to the next page.
                        if (redirectUrl) {
                            this.redirect(redirectUrl);
                        }
                    }
                }).done(function(response) {
                    // If we successfully enrolled, redirect the user
                    // to the next page (usually the student dashboard or payment flow)
                    if (response.redirect_destination) {
                        this.redirect(response.redirect_destination);
                    } else if (redirectUrl) {
                        this.redirect(redirectUrl);
                    }
                });
            },

            /**
             * Redirect to a URL.  Mainly useful for mocking out in tests.
             * @param  {string} url The URL to redirect to.
             */
            redirect: function(url) {
                window.location.href = url;
            }
        };

        return EnrollmentInterface;
    });
}).call(this, define || RequireJS.define);
