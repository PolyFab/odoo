# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestCrmCases
from odoo import fields
from datetime import date


class TestCrmMailActivity(TestCrmCases):

    def setUp(self):
        super(TestCrmMailActivity, self).setUp()
        # Set up activities
        Activity = self.env['mail.activity']
        self.activity3 = Activity.create({
            'name': 'Celebrate the sale',
            'days': 3,
            'description': 'ACT 3 : Beers for everyone because I am a good salesman !',
            'internal': True,
            'res_model': 'crm.lead',
        })
        self.activity2 = Activity.create({
            'name': 'Call for Demo',
            'days': 6,
            'description': 'ACT 2 : I want to show you my ERP !',
            'internal': True,
            'res_model': 'crm.lead',
        })
        self.activity1 = Activity.create({
            'name': 'Initial Contact',
            'days': 5,
            'description': 'ACT 1 : Presentation, barbecue, ... ',
            'internal': True,
            'res_model': 'crm.lead',
        })

        # I create an opportunity, as salesman
        self.partner_client = self.env.ref("base.res_partner_1")
        Lead = self.env['crm.lead'].sudo(self.crm_salesman.id)
        self.lead = Lead.create({
            'type': 'opportunity',
            'name': 'Test Opportunity Activity Log',
            'partner_id': self.partner_client.id,
            'team_id': self.env.ref("sales_team.team_sales_department").id,
            'user_id': self.crm_salesman.id,
        })

    def test_crm_activity_recipients(self):
        """ This test case check :
                - no internal subtype followed by client
                - activity subtype are not default ones
                - only activity followers are recipients when this kind of activity is logged
        """
        # Activity I'm going to log
        activity = self.activity2

        # Add explicitly a the client as follower
        self.lead.message_subscribe([self.partner_client.id])

        # Check the client is not follower of any internal subtype
        is_internal_subtype_for_client = self.lead.message_follower_ids.filtered(lambda fol: fol.partner_id.id == self.partner_client.id).mapped('subtype_ids.internal')
        self.assertFalse(any(is_internal_subtype_for_client), 'Partner client is following an internal subtype')

        # Add sale manager as follower of default subtypes
        self.lead.message_subscribe([self.crm_salemanager.partner_id.id])
        # Make the sale manager follower of the activity subtype
        manager_follower = self.env['mail.followers'].sudo().search([('res_model', '=', 'crm.lead'), ('res_id', '=', self.lead.id), ('partner_id', '=', self.crm_salemanager.partner_id.id)])
        manager_follower.write({
            'subtype_ids': [(4, activity.subtype_id.id)]
        })

        # trigger onchange and set the due date (date_action)
        ActivityLog = self.env['mail.activity.log'].sudo(self.crm_salesman.id)
        activity_log = ActivityLog.create({
            'next_activity_id': activity.id,
            'note': 'Content of the activity to log',
            'res_id': self.lead.id,
            'date_action': fields.Date.today(),
            'model': 'crm.lead'
        })
        activity_log.onchange_next_activity_id()
        activity_log.mark_as_done()

        # Check message recipients
        activity_message = self.lead.message_ids[0]
        self.assertEqual(activity_message.needaction_partner_ids, self.crm_salemanager.partner_id, 'Only the crm manager should be notified by the activity')
        self.assertEqual(self.lead.next_activity_id.id, False, 'When logging activity, the next activity planned is erased')

    def test_crm_activity_next_action(self):
        """ This test case set the next activity on a lead, log another, and schedule a third. """
        # Add the next activity (like we set it from a form view)
        activity_log = self.env['mail.activity.log'].sudo(self.crm_salesman.id).create({
            'next_activity_id': self.activity1.id,
            'date_action': fields.Date.today(),
            'res_id': self.lead.id,
            'model': 'crm.lead',
        })
        activity_log.onchange_next_activity_id()

        # Check the next activity is correct
        self.assertEqual(self.lead.title_action, self.activity1.description, 'Activity title should be the same on the lead and on the chosen activity')

        # Schedule the next activity
        activity_log.write({
            'next_activity_id': self.activity2.id,
            'note': 'Content of the activity to log',
        })
        activity_log.onchange_next_activity_id()
        activity_log.mark_as_done()

        # Check the next activity on the lead has been removed
        self.assertFalse(self.lead.next_activity_id.id, 'No next activity should be set on lead, since we jsut log another activity')

        # Schedule the next activity
        activity_log = self.env['mail.activity.log'].sudo(self.crm_salesman.id).create({
            'next_activity_id': self.activity3.id,
            'date_action': fields.Date.today(),
            'note': 'Content of the activity to log',
            'res_id': self.lead.id,
            'model': 'crm.lead',
        })
        activity_log.onchange_next_activity_id()

        # Check the activity is well scheldule on lead
        delta_days = (fields.Date.from_string(activity_log.date_action) - date.today()).days
        self.assertEqual(self.activity3.days, delta_days, 'The action date should be in the number of days set up on the activity 3')
        self.assertEqual(activity_log.title_action, self.activity3.description, 'Activity title should be the same on the lead and on the activity 3')
