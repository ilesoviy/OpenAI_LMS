$(document).ajaxError(function(event, jXHR) {
    if (jXHR.status === 403 && jXHR.responseText === 'Unauthenticated') {
        var message = gettext(
            'You have been logged out of your account. '
            + 'Click Okay to log in again now. '
            + 'Click Cancel to stay on this page '
            + '(you must log in again to save your work).'
        );

        if (window.confirm(message)) {
            var currentLocation = window.location.pathname;
            window.location.href = '/login?next=' + encodeURIComponent(currentLocation);
        }
    }
});
