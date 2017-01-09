# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from openerp import http

import datetime


class members_checkin(models.Model):
    _name = 'members.checkin'
    _order = 'id desc'

    partner = fields.Many2one('res.partner', string='Partner', ondelete='cascade', index=1)
    #membership_id = fields.Many2one('membership.membership_line', string="Membership", required=True)

    date_check_in = fields.Datetime(string='Check-in date', readonly=True)
    date_check_out = fields.Datetime(string='Check-out date', readonly=True)
    #duration =


class members(models.Model):
    _name = 'members.members'

    name = fields.Char(required=True)
    numberOfUpdates = fields.Integer('Number of updates',
                                     help='The number of times the scheduler has run and updated this field')
    lastModified = fields.Date('Last updated')

    def process_scheduler_queue(self, cr, uid, context=None):
        record_members = self.pool.get('res.partner')
        #record_members = http.request.env['res.partner']
        result_record = record_members.search(cr, uid, [('is_in', '=', True)], context=context)

        for partner in result_record:
            p = record_members.browse(cr, uid, partner, context=context)

            # modify the latest entry of the member in the check-in history
            record_checkin = self.pool.get('members.checkin')
            result_record_checkin = record_checkin.search(cr, uid, [('partner.partner_id_membership', '=', p.partner_id_membership)], context=context)
            if len(result_record_checkin) != 0:
                latest_record_checkin = record_checkin.browse(cr, uid, result_record_checkin[-1], context=context)
                latest_record_checkin.write({'date_check_out': fields.Datetime.now()})

            print "HELLOOOOO"
            m_status = p.compute_membership_state()

            print m_status
            p.write({'membership_state': m_status})

            p.write({'is_in': not p.is_in})


        scheduler_line_obj = self.pool.get('members.members')
        #record_members = http.request.env['res.partner']
        scheduler_line_ids = scheduler_line_obj.search(cr, uid, [])
        # Loops over every record in the model scheduler.demo
        for scheduler_line_id in scheduler_line_ids:
            # Contains all details from the record in the variable scheduler_line
            scheduler_line = scheduler_line_obj.browse(cr, uid, scheduler_line_id, context=context)
            numberOfUpdates = scheduler_line.numberOfUpdates
            # Update the record
            scheduler_line_obj.write(cr, uid, scheduler_line_id,
                                     {'numberOfUpdates': (numberOfUpdates + 1), 'lastModified': datetime.date.today()},
                                     context=context)

"""
    @api.depends('member_UID')
    def _search_partner(self):
        # Return info of membership
        if self.ids:
            ids_to_search = []
            for partner in self:
                if partner.associate_member:
                    ids_to_search.append(partner.associate_member.partner_id_membership)
                else:
                    ids_to_search.append(partner.partner_id_membership)
            self.env.cr.execute('''
                            SELECT
                                p.id as id,
                                MIN(m.date_from) as membership_start,
                                MAX(m.date_to) as membership_stop,
                                MIN(CASE WHEN m.date_cancel is not null THEN 1 END) as membership_cancel
                            FROM
                                res_partner p
                            LEFT JOIN
                                membership_membership_line m
                                ON (m.partner = p.id)
                            WHERE
                                p.id IN %s
                            GROUP BY
                                p.id''', (tuple(ids_to_search),))
            for record in self.env.cr.dictfetchall():
                partner = self.browse(record.pop('id')).update(record)
    """
