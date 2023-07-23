define(['backbone',
    'jquery',
    'underscore',
    'edx-ui-toolkit/js/utils/spec-helpers/ajax-helpers',
    'common/js/spec_helpers/template_helpers',
    'js/spec/views/fields_helpers',
    'string_utils'],
function(Backbone, $, _, AjaxHelpers, TemplateHelpers, FieldViewsSpecHelpers) {
    'use strict';

    var verifyAuthField = function(view, data, requests) {
        var selector = '.u-field-value .u-field-link-title-' + view.options.valueAttribute;

        spyOn(view, 'redirect_to');

        FieldViewsSpecHelpers.expectTitleAndMessageToContain(view, data.title, data.helpMessage);
        expect(view.$(selector).text().trim()).toBe('Unlink This Account');
        view.$(selector).click();
        FieldViewsSpecHelpers.expectMessageContains(view, 'Unlinking');
        AjaxHelpers.expectRequest(requests, 'POST', data.disconnectUrl);
        AjaxHelpers.respondWithNoContent(requests);

        expect(view.$(selector).text().trim()).toBe('Link Your Account');
        FieldViewsSpecHelpers.expectMessageContains(view, 'Successfully unlinked.');

        view.$(selector).click();
        FieldViewsSpecHelpers.expectMessageContains(view, 'Linking');
        expect(view.redirect_to).toHaveBeenCalledWith(data.connectUrl);
    };

    return {
        verifyAuthField: verifyAuthField
    };
});
