define(['backbone'], function(Backbone) {
    /**
     * Model used for metadata setting editors. This model does not do its own saving,
     * as that is done by module_edit.js.
     */
    var Metadata = Backbone.Model.extend({
        defaults: {
            field_name: null,
            display_name: null,
            value: null,
            explicitly_set: null,
            default_value: null,
            options: null,
            type: null,
            custom: false // Used only for non-metadata fields
        },

        initialize: function() {
            this.original_value = this.get('value');
            this.original_explicitly_set = this.get('explicitly_set');
        },

        /**
         * Returns true if the stored value is different, or if the "explicitly_set"
         * property has changed.
         */
        isModified: function() {
            // A non-metadata field will handle itself
            if (this.get('custom') === true) {
                return false;
            }

            if (!this.get('explicitly_set') && !this.original_explicitly_set) {
                return false;
            }
            if (this.get('explicitly_set') && this.original_explicitly_set) {
                return this.get('value') !== this.original_value;
            }
            return true;
        },

        /**
         * Returns true if a non-default/non-inherited value has been set.
         */
        isExplicitlySet: function() {
            return this.get('explicitly_set');
        },

        /**
         * The value, as shown in the UI. This may be an inherited or default value.
         */
        getDisplayValue: function() {
            return this.get('value');
        },

        /**
         * The value, as should be returned to the server. if 'isExplicitlySet'
         * returns false, this method returns null to indicate that the value
         * is not set at this level.
         */
        getValue: function() {
            return this.get('explicitly_set') ? this.get('value') : null;
        },

        /**
         * Sets the displayed value.
         */
        setValue: function(value) {
            this.set({
                explicitly_set: true,
                value: value
            });
        },

        /**
         * Returns the field name, which should be used for persisting the metadata
         * field to the server.
         */
        getFieldName: function() {
            return this.get('field_name');
        },

        /**
         * Returns the options. This may be a array of possible values, or an object
         * with properties like "max", "min" and "step".
         */
        getOptions: function() {
            return this.get('options');
        },

        /**
         * Returns the type of this metadata field. Possible values are SELECT_TYPE,
         * INTEGER_TYPE, and FLOAT_TYPE, GENERIC_TYPE.
         */
        getType: function() {
            return this.get('type');
        },

        /**
         * Reverts the value to the default_value specified at construction, and updates the
         * explicitly_set property.
         */
        clear: function() {
            this.set({
                explicitly_set: false,
                value: this.get('default_value')
            });
        }
    });

    Metadata.SELECT_TYPE = 'Select';
    Metadata.INTEGER_TYPE = 'Integer';
    Metadata.FLOAT_TYPE = 'Float';
    Metadata.GENERIC_TYPE = 'Generic';
    Metadata.LIST_TYPE = 'List';
    Metadata.DICT_TYPE = 'Dict';
    Metadata.VIDEO_LIST_TYPE = 'VideoList';
    Metadata.RELATIVE_TIME_TYPE = 'RelativeTime';

    return Metadata;
});
