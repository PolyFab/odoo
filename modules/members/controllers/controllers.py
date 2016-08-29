# -*- coding: utf-8 -*-
from openerp import http
from openerp.http import request
from openerp import SUPERUSER_ID

class Members(http.Controller):
    @http.route('/members/members/', auth='public')
    def access(self, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        record_members = http.request.env['res.partner']

        if not record_members:
            return http.request.render('members.member_display', {'id': 'None', 'name': 'None'})

        return http.request.render('members.member_display', {'members': record_members.search(cr, SUPERUSER_ID, [('name', '=', 'Benjamin De Leener')], context=context)})

