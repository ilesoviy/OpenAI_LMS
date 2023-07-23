/* eslint-env node */

// Karma config for cms suite.
// Docs and troubleshooting tips in common/static/common/js/karma.common.conf.js

'use strict';

var path = require('path');

var configModule = require(path.join(__dirname, '../../common/static/common/js/karma.common.conf.js'));

var options = {

    includeCommonFiles: true,

    libraryFiles: [],

    libraryFilesToInclude: [
    ],

    // Make sure the patterns in sourceFiles and specFiles do not match the same file.
    // Otherwise Istanbul which is used for coverage tracking will cause tests to not run.
    sourceFiles: [],
    //     {pattern: 'js/factories/login.js', webpack: true},
    //     {pattern: 'js/factories/xblock_validation.js', webpack: true},
    //     {pattern: 'js/factories/container.js', webpack: true},
    //     {pattern: 'js/factories/context_course.js', webpack: true},
    //     {pattern: 'js/factories/edit_tabs.js', webpack: true},
    //     {pattern: 'js/factories/library.js', webpack: true},
    //     {pattern: 'js/factories/textbooks.js', webpack: true},
    // ],

    // All spec files should be imported in main_webpack.js, rather than being listed here
    specFiles: [],

    fixtureFiles: [
        {pattern: '../templates/js/**/*.underscore'},
        {pattern: 'templates/**/*.underscore'}
    ],

    runFiles: [
        {pattern: 'cms/js/spec/main_webpack.js', webpack: true},
        {pattern: 'jasmine.cms.conf.js', included: true}
    ],

    preprocessors: {}
};

options.runFiles
    .filter(function(file) { return file.webpack; })
    .forEach(function(file) {
        options.preprocessors[file.pattern] = ['webpack'];
    });

module.exports = function(config) {
    configModule.configure(config, options);
};
