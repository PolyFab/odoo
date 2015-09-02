odoo.define('web_editor.backend', function (require) {
'use strict';

var core = require('web.core');
var session = require('web.session');
var Model = require('web.DataModel');
var common = require('web.form_common');
var base = require('web_editor.base');
var editor = require('web_editor.editor');
var summernote = require('web_editor.summernote');
var transcoder = require('web_editor.transcoder');

var QWeb = core.qweb;
var _t = core._t;

/**
 * FieldTextHtml Widget
 * Intended for FieldText widgets meant to display HTML content. This
 * widget will instantiate an iframe with the editor summernote improved by odoo
 */

var widget = common.AbstractField.extend(common.ReinitializeFieldMixin);

var FieldTextHtmlSimple = widget.extend({
    template: 'web_editor.FieldTextHtmlSimple',
    _config: function () {
        var self = this;
        return {
            'focus': false,
            'height': 180,
            'toolbar': [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['fontsize', ['fontsize']],
                ['color', ['color']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['table', ['table']],
                ['insert', ['link', 'picture']],
                ['history', ['undo', 'redo']]
            ],
            'styleWithSpan': false,
            'inlinemedia': ['p'],
            'lang': "odoo",
            'onChange': function (value) {
                self.internal_set_value(value);
                self.trigger('changed_value');
            }
        };
    },
    initialize_content: function() {
        var self = this;
        this.$textarea = this.$("textarea").val(this.get('value') || "<p><br/></p>");

        if (this.get("effective_readonly")) {
            this.$textarea.hide().after('<div class="note-editable"/>');
        } else {
            this.$textarea.summernote(this._config());

            if (this.field.translate && this.view) {
                $(QWeb.render('web_editor.FieldTextHtml.button.translate', {'widget': this}))
                    .appendTo(this.$('.note-toolbar'))
                    .on('click', this.on_translate);
            }

            var reset = _.bind(this.reset_history, this);
            this.view.on('load_record', this, reset);
            setTimeout(reset, 0);
        }
        this.$content = this.$('.note-editable:first');

        $(".oe-view-manager-content").on("scroll", function () {
            $('.o_table_handler').remove();
        });
        this._super();
    },
    reset_history: function () {
        var history = this.$content.data('NoteHistory');
        if (history) {
            history.reset();
            self.$('.note-toolbar').find('button[data-event="undo"]').attr('disabled', true);
        }
    },
    text_to_html: function (text) {
        var value = text || "";
        if (value.match(/^\s*$/)) {
            value = '<p><br/></p>';
        } else {
            value = "<p>"+value.split(/<br\/?>/).join("</p><p>")+"</p>";
            value = value.replace('<p><p>', '<p>').replace('</p></p>', '</p>');
        }
        return value;
    },
    focus: function() {
        var input = !this.get("effective_readonly") && this.$textarea;
        return input ? input.focus() : false;
    },
    render_value: function() {
        var value = this.get('value');
        this.$textarea.val(value || '');
        this.$content.html(this.text_to_html(value));
        this.$content.focusInEnd();
        var history = this.$content.data('NoteHistory');
        if (history && history.recordUndo()) {
            this.$('.note-toolbar').find('button[data-event="undo"]').attr('disabled', false);
        }
    },
    is_false: function() {
        return !this.get('value') || this.get('value') === "<p><br/></p>" || !this.get('value').match(/\S/);
    },
    before_save: function() {
        if (this.options['style-inline']) {
            transcoder.class_to_style(this.$content);
            transcoder.font_to_img(this.$content);
            this.internal_set_value(this.$content.html());
        }
    },
    destroy_content: function () {
        $(".oe-view-manager-content").off("scroll");
        this.$textarea.destroy();
        this._super();
    }
});

var FieldTextHtml = widget.extend({
    template: 'web_editor.FieldTextHtml',
    willStart: function () {
        var self = this;
        return new Model('res.lang').call("search_read", [[['code', '!=', 'en_US']], ["name", "code"]]).then(function (res) {
            self.languages = res;
        });
    },
    start: function () {
        var self = this;

        this.callback = _.uniqueId('FieldTextHtml_');
        window.odoo[this.callback+"_editor"] = function (EditorBar) {
            setTimeout(function () {
                self.on_editor_loaded(EditorBar);
            },0);
        };
        window.odoo[this.callback+"_content"] = function (EditorBar) {
            self.on_content_loaded();
        };
        window.odoo[this.callback+"_updown"] = null;
        window.odoo[this.callback+"_downup"] = function (value) {
            self.internal_set_value(value);
            self.trigger('changed_value');
            self.resize();
        };

        // init jqery objects
        this.$iframe = this.$el.find('iframe');
        this.document = null;
        this.$body = $();
        this.$content = $();

        this.$iframe.css('min-height', 'calc(100vh - 360px)');

        // init resize
        this.resize = function resize() {
            if (self.get('effective_readonly')) { return; }
            if ($("body").hasClass("o_form_FieldTextHtml_fullscreen")) {
                self.$iframe.css('height', (document.body.clientHeight - self.$iframe.offset().top) + 'px');
            } else {
                self.$iframe.css("height", (self.$body.find("#oe_snippets").length ? 500 : 300) + "px");
            }
        };
        $(window).on('resize', self.resize);

        return this._super();
    },
    get_url: function (_attr) {
        var src = this.options.editor_url ? this.options.editor_url+"?" : "/web_editor/field/html?";
        var datarecord = this.view.get_fields_values();

        var attr = {
            'model': this.view.model,
            'field': this.name,
            'res_id': datarecord.id || '',
            'callback': this.callback
        };
        _attr = _attr || {};

        if (this.options['style-inline']) {
            attr.inline_mode = 1;
        }
        if (this.options.snippets) {
            attr.snippets = this.options.snippets;
        }
        if (!this.get("effective_readonly")) {
            attr.enable_editor = 1;
        }
        if (this.field.translate) {
            attr.translatable = 1;
        }
        if (session.debug) {
            attr.debug = 1;
        }

        attr.lang = attr.enable_editor ? 'en_US' : this.session.user_context.lang;

        for (var k in _attr) {
            attr[k] = _attr[k];
        }

        for (var k in attr) {
            if (attr[k] !== null) {
                src += "&"+k+"="+(_.isBoolean(attr[k]) ? +attr[k] : attr[k]);
            }
        }

        delete datarecord[this.name];
        src += "&datarecord="+ encodeURIComponent(JSON.stringify(datarecord));

        return src;
    },
    initialize_content: function() {
        this.$el.closest('.modal-body').css('max-height', 'none');
        this.$iframe = this.$el.find('iframe');
        this.document = null;
        this.$body = $();
        this.$content = $();
        this.editor = false;
        window.odoo[this.callback+"_updown"] = null;
        this.$iframe.attr("src", this.get_url());
    },
    on_content_loaded: function () {
        var self = this;
        this.document = this.$iframe.contents()[0];
        this.$body = $("body", this.document);
        this.$content = this.$body.find("#editable_area");
        this.lang = this.$iframe.attr('src').match(/[?&]lang=([^&]+)/);
        this.lang = this.lang ? this.lang[1] : this.view.dataset.context.lang;
        this._dirty_flag = false;
        this.render_value();
        setTimeout(function () {
            self.add_button();
            setTimeout(self.resize,0);
        }, 0);
    },
    on_editor_loaded: function (EditorBar) {
        var self = this;
        this.editor = EditorBar;
        if (this.get('value') && window.odoo[self.callback+"_updown"] && !(this.$content.html()||"").length) {
            this.render_value();
        }
        setTimeout(function () {
            setTimeout(self.resize,0);
        }, 0);
    },
    add_button: function () {
        var self = this;
        var $to = this.$body.find("#web_editor-top-edit, #wrapwrap").first();

        $(QWeb.render('web_editor.FieldTextHtml.translate', {'widget': this}))
            .appendTo($to)
            .on('change', 'select', function () {
                var lang = $(this).val();
                var edit = !self.get("effective_readonly");
                var trans = lang !== 'en_US';
                self.$iframe.attr("src", self.get_url({
                    'edit_translations': edit && trans,
                    'enable_editor': edit && !trans,
                    'lang': lang
                }));
            });

        $(QWeb.render('web_editor.FieldTextHtml.fullscreen'))
            .appendTo($to)
            .on('click', '.o_fullscreen', function () {
                $("body").toggleClass("o_form_FieldTextHtml_fullscreen");
                var full = $("body").hasClass("o_form_FieldTextHtml_fullscreen");
                self.$iframe.parents().toggleClass('o_form_fullscreen_ancestor', full);
                self.resize();
            });

        this.$body.on('click', '[data-action="cancel"]', function (event) {
            event.preventDefault();
            self.initialize_content();
        });
    },
    render_value: function() {
        if (this.lang !== this.view.dataset.context.lang || this.$iframe.attr('src').match(/[?&]edit_translations=1/)) {
            return;
        }
        var value = (this.get('value') || "").replace(/^<p[^>]*>(\s*|<br\/?>)<\/p>$/, '');
        if (!this.$content) {
            return;
        }
        if (!this.get("effective_readonly")) {
            if(window.odoo[this.callback+"_updown"]) {
                window.odoo[this.callback+"_updown"](value, this.view.get_fields_values(), this.name);
                this.resize();
            }
        } else {
            this.$content.html(value);
            this.$iframe.css("height", (this.$body.height()+20) + "px");
        }
    },
    is_false: function() {
        return this.get('value') === false || !this.$content.html() || !this.$content.html().match(/\S/);
    },
    before_save: function () {
        if (this.lang !== 'en_US' && this.$body.find('.o_dirty').length) {
            this.internal_set_value( this.view.datarecord[this.name] );
            this._dirty_flag = false;
            return this.editor.save();
        } else if (this._dirty_flag && this.editor && this.editor.buildingBlock) {
            this.editor.buildingBlock.clean_for_save();

            // escape text nodes for xml saving
            var $escaped_el = this.$content.clone();
            $escaped_el.find('*').addBack().not('script,style').contents().each(function(){
                if(this.nodeType == 3) {
                    this.nodeValue = _.escape(this.nodeValue);
                }
            });
            this.internal_set_value( $escaped_el.html() );
        }
    },
    destroy: function () {
        $(window).off('resize', self.resize);
        delete window.odoo[this.callback+"_editor"];
        delete window.odoo[this.callback+"_content"];
        delete window.odoo[this.callback+"_updown"];
        delete window.odoo[this.callback+"_downup"];
    }
});

core.form_widget_registry
    .add('html', FieldTextHtmlSimple)
    .add('html_frame', FieldTextHtml);

});
