# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from functools import partial
from openerp.osv import fields, osv
from openerp.tools.translate import _


class ResPartner(osv.osv):
    _inherit = 'res.partner'

    def _get_event_resource_assignment_mode(self, cr, uid, context=None):
        return [
            ('automatic', 'Automatic'),
            ('manual', 'Manual'),
        ]

    _columns = {
        'speaker': fields.boolean('Speaker', help="Check this box if this contact is a speaker."),
        'room': fields.boolean('Room', help='Check this box if this contact address could be used as room location'),
        'room_max_seats': fields.integer('Max seats', help='Max seats available in the room. Use 0 for unlimited seats'),
        'equipment': fields.boolean('Equipment', help='Check this box if this contact can be used as a event equipment (like a beamer, ...)'),
        'event_ids': fields.one2many('event.event', 'main_speaker_id', readonly=True),
        'event_registration_ids': fields.one2many('event.registration', 'partner_id', readonly=True),
        'speakerinfo_ids': fields.one2many('event.course.speakerinfo', 'speaker_id', 'Speaker Infos'),
        'child_ids': fields.one2many('res.partner', 'parent_id', 'Contacts', domain=[('active', '=', True), ('room', '=', False), ('equipment', '=', False)]),  # force "active_test" domain to bypass _search() override
        'room_ids': fields.one2many('res.partner', 'parent_id', 'Rooms', domain=[('active', '=', True), ('room', '=', True)]),
        'equipment_ids': fields.one2many('res.partner', 'parent_id', 'Equipments', domain=[('active', '=', True), ('equipment', '=', True)]),
        'external': fields.boolean('External', help='This resource is an external resource'),
        'event_assignment_mode': fields.selection(_get_event_resource_assignment_mode, 'Assignment Mode', required=True),
    }

    _defaults = {
        'event_assignment_mode': 'automatic',
    }

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}

        call_change_role = partial(self.onchange_event_role,
                                   cr, uid, [], context=context)
        for i, f in enumerate(['speaker', 'room', 'equipment']):
            if values.get(f):
                changes = call_change_role(f, *[True if j == i else False
                                                for j in xrange(3)])
                for k, v in changes.get('value', {}).iteritems():
                    if k not in values:
                        values[k] = v
                break

        return super(ResPartner, self).create(cr, uid, values, context=context)

    def open_registrations(self, cr, uid, ids, context=None):
        """ Utility method used to add an "Open Registrations" button in partner views """
        partner = self.browse(cr, uid, ids[0], context=context)
        if partner.customer:
            return {'type': 'ir.actions.act_window',
                    'name': _('Registrations'),
                    'res_model': 'event.registration',
                    'view_type': 'form',
                    'view_mode': 'tree,form,calendar,graph',
                    'context': "{'search_default_partner_id': active_id}"}
        return {}

    def open_events(self, cr, uid, ids, context=None):
        """ Utility method used to add an "Open Events" button in partner views """
        partner = self.browse(cr, uid, ids[0], context=context)
        partner_domain = [
            '|', '|',
            ('registration_ids.partner_id', '=', partner.id),
            ('main_speaker_id', '=', partner.id),
            ('address_id', '=', partner.id),
        ]
        return {'type': 'ir.actions.act_window',
                'name': _('Events'),
                'res_model': 'event.event',
                'view_type': 'form',
                'view_mode': 'tree,form,calendar,graph',
                'domain': partner_domain}

    def open_courses(self, cr, uid, ids, context=None):
        """ Utility method used to add an "Open Courses" button in partner views """
        partner = self.browse(cr, uid, ids[0], context=context)
        if partner.speaker:
            return {
                'name': _('Courses'),
                'type': 'ir.actions.act_window',
                'res_model': 'event.course',
                'view_type': 'form',
                'view_mode': 'kanban,form,tree',
                'context': "{'search_default_speaker_id': active_id}",
            }
        return {}

    def onchange_event_role(self, cr, uid, ids, source, speaker, room, equipment, context=None):
        roles = dict(speaker=speaker, room=room, equipment=equipment)
        roles_update = dict(speaker=dict(attendee_type='speaker'),
                            room=dict(attendee_type='room'),
                            equipment=dict(attendee_type='resource'))
        values = {}
        if all(not v for v in roles.itervalues()):
            values.update(attendee_type='person')
            return {'value': values}
        for field, value in roles.iteritems():
            if value and source == field:
                # update related fields and set other roles to False
                values.update(roles_update.get(field, {}))
                values.update(dict((r, False) for r in roles if r != field and roles[r]))
                break
        return {'value': values}

    def onchange_external(self, cr, uid, ids, external, context=None):
        values = {
            'attendee_external': bool(external),
        }
        return {'value': values}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
