# -*- coding: utf-8 -*-
import base64
from urllib.parse import quote_plus
from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError


class AdaptFitAdminPortal(http.Controller):

    def _get_selection_labels(self, model_name, field_name):
        model = request.env[model_name]
        return dict(model._fields[field_name].selection)

    @http.route('/adaptfit/admin', type='http', auth='user', website=False)
    def admin_dashboard(self, tab='overview', q='', stage='', msg='', err='', **kwargs):
        Order = request.env['adaptive.order']
        Partner = request.env['res.partner']
        QaCheck = request.env['adaptive.qa.check']
        Settlement = request.env['adaptive.artisan.settlement']

        all_orders = Order.search([], order='urgency_level desc, create_date desc')
        active_orders = all_orders.filtered(lambda o: o.state not in ('delivered', 'cancel'))
        rush_orders = active_orders.filtered(lambda o: o.urgency_level == 'clinical_rush')
        delivered_orders = all_orders.filtered(lambda o: o.state == 'delivered')

        # Filtered orders for Orders tab
        order_domain = []
        if stage:
            order_domain.append(('state', '=', stage))
        if q:
            order_domain += ['|', '|', ('name', 'ilike', q), ('patient_ref', 'ilike', q), ('partner_id.name', 'ilike', q)]
        filtered_orders = Order.search(order_domain, order='urgency_level desc, create_date desc') if (stage or q) else all_orders

        # Patients
        patient_domain = [('is_adaptive_patient', '=', True)]
        if q and tab == 'patients':
            patient_domain += ['|', ('name', 'ilike', q), ('patient_identifier', 'ilike', q)]
        patients = Partner.search(patient_domain, order='create_date desc')

        # QA Checks & Settlements
        qa_checks = QaCheck.search([], order='create_date desc')
        pending_qa = qa_checks.filtered(lambda c: c.state == 'pending')
        settlements = Settlement.search([], order='create_date desc')
        pending_payout_total = sum(settlements.filtered(lambda s: s.state != 'paid').mapped('total_payout'))

        # ESG Totals
        total_co2 = round(sum(all_orders.mapped('eco_carbon_saved_kg')), 2)
        total_water = round(sum(all_orders.mapped('eco_water_saved_l')), 1)
        total_yardage = round(sum(all_orders.mapped('calculated_yardage')), 2)

        # Stage pipeline counts
        stage_labels = self._get_selection_labels('adaptive.order', 'state')
        garment_labels = self._get_selection_labels('adaptive.order', 'garment_type')
        urgency_labels = self._get_selection_labels('adaptive.order', 'urgency_level')

        stage_counts = []
        for key in ('draft', 'pattern', 'stitching', 'transit', 'fitting', 'delivered'):
            stage_counts.append({
                'key': key,
                'label': stage_labels.get(key, key),
                'count': len(all_orders.filtered(lambda o, k=key: o.state == k)),
            })

        # Lookup lists for Create Order modal
        fabrics = request.env['product.product'].search([('is_sustainable_fabric', '=', True)])
        artisans = request.env['res.users'].search([('share', '=', False)])
        all_patients = Partner.search([('is_adaptive_patient', '=', True)], order='name asc')

        return request.render('adaptfit_apparel.admin_portal_template', {
            'tab': tab,
            'q': q,
            'stage': stage,
            'msg': msg,
            'err': err,
            'user': request.env.user,
            'kpi': {
                'active_count': len(active_orders),
                'rush_count': len(rush_orders),
                'delivered_count': len(delivered_orders),
                'patient_count': len(all_patients),
                'pending_qa_count': len(pending_qa),
                'pending_payout_total': round(pending_payout_total, 2),
                'total_co2': total_co2,
                'total_water': total_water,
                'total_yardage': total_yardage,
            },
            'stage_counts': stage_counts,
            'stage_labels': stage_labels,
            'garment_labels': garment_labels,
            'urgency_labels': urgency_labels,
            'orders': filtered_orders,
            'recent_orders': all_orders[:6],
            'patients': patients,
            'qa_checks': qa_checks,
            'settlements': settlements,
            'fabrics': fabrics,
            'artisans': artisans,
            'all_patients': all_patients,
        })

    @http.route('/adaptfit/admin/order/create', type='http', auth='user', methods=['POST'], website=False)
    def admin_create_order(self, partner_id=None, fabric_id=None, garment_type='shirt_top',
                           urgency_level='standard', artisan_id=None, clinical_notes_input='', **kwargs):
        if not partner_id or not fabric_id:
            return request.redirect('/adaptfit/admin?tab=orders&err=' + quote_plus(_('Patient and Sustainable Fabric are required.')))

        vals = {
            'partner_id': int(partner_id),
            'fabric_id': int(fabric_id),
            'garment_type': garment_type,
            'urgency_level': urgency_level,
            'clinical_notes_input': clinical_notes_input or '',
        }
        if artisan_id:
            vals['artisan_id'] = int(artisan_id)

        order = request.env['adaptive.order'].create(vals)
        return request.redirect(f'/adaptfit/admin?tab=orders&msg=' + quote_plus(_('Order %s created.') % order.name))

    @http.route('/adaptfit/admin/order/<int:order_id>/stage', type='http', auth='user', methods=['POST'], website=False)
    def admin_update_order_stage(self, order_id, target_state='', **kwargs):
        order = request.env['adaptive.order'].browse(order_id).exists()
        valid_states = ('draft', 'pattern', 'stitching', 'transit', 'fitting', 'delivered', 'cancel')
        if order and target_state in valid_states:
            order.write({'state': target_state})
            stage_label = dict(order._fields['state'].selection).get(target_state, target_state)
            order.message_post(body=_('Command Center updated stage to: %s') % stage_label)
            return request.redirect('/adaptfit/admin?tab=orders&msg=' + quote_plus(_('%s moved to %s') % (order.name, stage_label)))
        return request.redirect('/adaptfit/admin?tab=orders')

    @http.route('/adaptfit/admin/patient/create', type='http', auth='user', methods=['POST'], website=False)
    def admin_create_patient(self, name='', email='', phone='', medical_notes='', photo=None, **kwargs):
        if not name.strip():
            return request.redirect('/adaptfit/admin?tab=patients&err=' + quote_plus(_('Patient name is required.')))

        vals = {
            'name': name.strip(),
            'email': email.strip() or False,
            'phone': phone.strip() or False,
            'is_adaptive_patient': True,
            'medical_notes': medical_notes.strip() or False,
            'condition_amputation': bool(kwargs.get('condition_amputation')),
            'condition_stroke_mobility': bool(kwargs.get('condition_stroke_mobility')),
            'condition_medical_port': bool(kwargs.get('condition_medical_port')),
            'condition_wheelchair': bool(kwargs.get('condition_wheelchair')),
            'condition_sensory': bool(kwargs.get('condition_sensory')),
            'pref_magnetic_closures': bool(kwargs.get('pref_magnetic_closures')),
            'pref_flatlock_seams': bool(kwargs.get('pref_flatlock_seams')),
        }
        if photo and hasattr(photo, 'read'):
            raw = photo.read()
            if raw:
                vals['image_1920'] = base64.b64encode(raw)

        partner = request.env['res.partner'].create(vals)
        return request.redirect('/adaptfit/admin?tab=patients&msg=' + quote_plus(_('Patient %s registered (%s).') % (partner.name, partner.patient_identifier)))

    @http.route('/adaptfit/admin/patient/<int:partner_id>/photo', type='http', auth='user', methods=['POST'], website=False)
    def admin_upload_patient_photo(self, partner_id, photo=None, **kwargs):
        partner = request.env['res.partner'].browse(partner_id).exists()
        if partner and photo and hasattr(photo, 'read'):
            raw = photo.read()
            if raw:
                partner.write({'image_1920': base64.b64encode(raw)})
                return request.redirect('/adaptfit/admin?tab=patients&msg=' + quote_plus(_('Profile picture updated for %s.') % partner.name))
        return request.redirect('/adaptfit/admin?tab=patients&err=' + quote_plus(_('Please select an image file.')))

    @http.route('/adaptfit/admin/qa/<int:qa_id>/action', type='http', auth='user', methods=['POST'], website=False)
    def admin_qa_action(self, qa_id, action='pass', rework_reason='', **kwargs):
        qa = request.env['adaptive.qa.check'].browse(qa_id).exists()
        if not qa:
            return request.redirect('/adaptfit/admin?tab=qa')
        try:
            if action == 'pass':
                qa.write({
                    'tactile_seam_audit': True,
                    'asymmetric_tolerance_ok': True,
                    'magnetic_polarity_test': bool(kwargs.get('magnetic_polarity_test', True)),
                    'port_access_clearance': bool(kwargs.get('port_access_clearance', True)),
                })
                qa.action_pass_qa()
                return request.redirect('/adaptfit/admin?tab=qa&msg=' + quote_plus(_('QA %s passed.') % qa.name))
            elif action == 'rework':
                if rework_reason.strip():
                    qa.write({'rework_reason': rework_reason.strip()})
                qa.action_flag_rework()
                return request.redirect('/adaptfit/admin?tab=qa&msg=' + quote_plus(_('QA %s flagged for rework.') % qa.name))
        except UserError as e:
            return request.redirect('/adaptfit/admin?tab=qa&err=' + quote_plus(str(e)))
        return request.redirect('/adaptfit/admin?tab=qa')

    @http.route('/adaptfit/admin/settlement/<int:settlement_id>/action', type='http', auth='user', methods=['POST'], website=False)
    def admin_settlement_action(self, settlement_id, action='confirm', **kwargs):
        rec = request.env['adaptive.artisan.settlement'].browse(settlement_id).exists()
        if not rec:
            return request.redirect('/adaptfit/admin?tab=settlements')
        if action == 'fetch':
            rec.action_fetch_completed_orders()
        elif action == 'confirm':
            rec.action_confirm()
        elif action == 'paid':
            rec.action_mark_paid()
        return request.redirect('/adaptfit/admin?tab=settlements&msg=' + quote_plus(_('Settlement %s updated.') % rec.name))

    @http.route('/adaptfit/admin/order/<int:order_id>/update', type='http', auth='user', methods=['POST'], website=False)
    def admin_update_order(self, order_id, **kwargs):
        order = request.env['adaptive.order'].browse(order_id).exists()
        if not order:
            return request.redirect('/adaptfit/admin?tab=orders')
        vals = {
            'partner_id': int(kwargs['partner_id']) if kwargs.get('partner_id') else order.partner_id.id,
            'garment_type': kwargs.get('garment_type') or order.garment_type,
            'fabric_id': int(kwargs['fabric_id']) if kwargs.get('fabric_id') else order.fabric_id.id,
            'urgency_level': kwargs.get('urgency_level') or order.urgency_level,
            'artisan_id': int(kwargs['artisan_id']) if kwargs.get('artisan_id') else False,
            'clinical_notes_input': kwargs.get('clinical_notes_input', ''),
            'has_magnetic_placket': bool(kwargs.get('has_magnetic_placket')),
            'has_port_access_zip': bool(kwargs.get('has_port_access_zip')),
            'has_flatlock_frictionless': bool(kwargs.get('has_flatlock_frictionless')),
            'has_high_seated_rise': bool(kwargs.get('has_high_seated_rise')),
            'has_tagless_label': bool(kwargs.get('has_tagless_label')),
        }
        if kwargs.get('total_amount'):
            vals['total_amount'] = float(kwargs['total_amount'])
        if kwargs.get('advance_deposit') not in (None, ''):
            vals['advance_deposit'] = float(kwargs['advance_deposit'])
        order.write(vals)
        return request.redirect('/adaptfit/admin?tab=orders&msg=' + quote_plus(_('Order %s updated.') % order.name))

    @http.route('/adaptfit/admin/patient/<int:partner_id>/update', type='http', auth='user', methods=['POST'], website=False)
    def admin_update_patient(self, partner_id, photo=None, **kwargs):
        partner = request.env['res.partner'].browse(partner_id).exists()
        if not partner:
            return request.redirect('/adaptfit/admin?tab=patients')
        vals = {
            'name': (kwargs.get('name') or partner.name).strip(),
            'email': (kwargs.get('email') or '').strip() or False,
            'phone': (kwargs.get('phone') or '').strip() or False,
            'medical_notes': (kwargs.get('medical_notes') or '').strip() or False,
            'condition_amputation': bool(kwargs.get('condition_amputation')),
            'condition_stroke_mobility': bool(kwargs.get('condition_stroke_mobility')),
            'condition_medical_port': bool(kwargs.get('condition_medical_port')),
            'condition_wheelchair': bool(kwargs.get('condition_wheelchair')),
            'condition_sensory': bool(kwargs.get('condition_sensory')),
            'pref_magnetic_closures': bool(kwargs.get('pref_magnetic_closures')),
            'pref_flatlock_seams': bool(kwargs.get('pref_flatlock_seams')),
        }
        if photo and hasattr(photo, 'read'):
            raw = photo.read()
            if raw:
                vals['image_1920'] = base64.b64encode(raw)
        partner.write(vals)
        return request.redirect('/adaptfit/admin?tab=patients&msg=' + quote_plus(_('Patient %s updated.') % partner.name))

    @http.route('/adaptfit/admin/qa/<int:qa_id>/update', type='http', auth='user', methods=['POST'], website=False)
    def admin_update_qa(self, qa_id, **kwargs):
        qa = request.env['adaptive.qa.check'].browse(qa_id).exists()
        if not qa:
            return request.redirect('/adaptfit/admin?tab=qa')
        qa.write({
            'tactile_seam_audit': bool(kwargs.get('tactile_seam_audit')),
            'magnetic_polarity_test': bool(kwargs.get('magnetic_polarity_test')),
            'port_access_clearance': bool(kwargs.get('port_access_clearance')),
            'asymmetric_tolerance_ok': bool(kwargs.get('asymmetric_tolerance_ok')),
            'rework_reason': (kwargs.get('rework_reason') or '').strip() or False,
        })
        return request.redirect('/adaptfit/admin?tab=qa&msg=' + quote_plus(_('QA Checklist %s saved.') % qa.name))

    @http.route('/adaptfit/admin/settlement/<int:settlement_id>/update', type='http', auth='user', methods=['POST'], website=False)
    def admin_update_settlement(self, settlement_id, **kwargs):
        rec = request.env['adaptive.artisan.settlement'].browse(settlement_id).exists()
        if not rec:
            return request.redirect('/adaptfit/admin?tab=settlements')
        vals = {}
        if kwargs.get('complexity_bonus') not in (None, ''):
            vals['complexity_bonus'] = float(kwargs['complexity_bonus'])
        if kwargs.get('defect_penalty') not in (None, ''):
            vals['defect_penalty'] = float(kwargs['defect_penalty'])
        if vals:
            rec.write(vals)
        return request.redirect('/adaptfit/admin?tab=settlements&msg=' + quote_plus(_('Settlement %s updated.') % rec.name))
