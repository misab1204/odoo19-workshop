# -*- coding: utf-8 -*-
import json
from odoo import http, _
from odoo.http import request
from odoo.tools import html2plaintext

URGENCY_PRIORITY = {
    'clinical_rush': 0,
    'urgent': 1,
    'standard': 2,
}


class ArtisanChatController(http.Controller):

    def _is_ajax(self, **kwargs):
        return (
            kwargs.get('ajax') == '1'
            or request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest'
        )

    def _serialize_message(self, message, is_system=False):
        text_body = html2plaintext(message.body or '').strip()
        img_attachments = message.attachment_ids.filtered(
            lambda a: a.mimetype and a.mimetype.startswith('image/')
        )
        return {
            'id': message.id,
            'author': message.author_id.name or _('System'),
            'is_me': message.author_id.id == request.env.user.partner_id.id,
            'is_system': is_system,
            'time': message.date.strftime('%H:%M') if message.date else '',
            'body': text_body,
            'image_ids': img_attachments.ids,
        }

    def _get_order_cards(self):
        orders = request.env['adaptive.order'].search([
            ('state', 'in', ('draft', 'pattern', 'stitching', 'transit')),
        ], order='create_date desc')

        sorted_orders = sorted(
            orders,
            key=lambda o: (
                URGENCY_PRIORITY.get(o.urgency_level, 99),
                -(o.create_date.timestamp() if o.create_date else 0),
            ),
        )

        order_cards = []
        for o in sorted_orders:
            last_msg = o.message_ids.filtered(
                lambda m: m.message_type in ('comment', 'email') and m.body
            )[:1]
            preview = (
                html2plaintext(last_msg.body).strip()[:75]
                if last_msg
                else _("Ready for workshop review")
            )
            last_time = (
                last_msg.date.strftime('%H:%M')
                if last_msg and last_msg.date
                else (o.create_date.strftime('%H:%M') if o.create_date else '')
            )
            order_cards.append({
                'order': o,
                'garment_label': dict(o._fields['garment_type'].selection).get(o.garment_type, ''),
                'state_label': dict(o._fields['state'].selection).get(o.state, ''),
                'preview': preview,
                'last_time': last_time,
            })
        return order_cards

    @http.route('/adaptfit/artisan', type='http', auth='user', website=False)
    def artisan_chat_list(self, **kwargs):
        return request.render('adaptfit_apparel.artisan_chat_list_template', {
            'order_cards': self._get_order_cards(),
            'artisan_user': request.env.user,
        })

    @http.route('/adaptfit/artisan/<int:order_id>', type='http', auth='user', website=False)
    def artisan_chat_detail(self, order_id, **kwargs):
        order = request.env['adaptive.order'].browse(order_id).exists()
        if not order:
            return request.redirect('/adaptfit/artisan')

        messages = order.message_ids.filtered(
            lambda m: m.message_type in ('comment', 'notification', 'email')
            and (m.body or m.attachment_ids)
        ).sorted(key=lambda m: m.date)

        chat_messages = []
        for m in messages:
            text_body = html2plaintext(m.body or '').strip()
            img_attachments = m.attachment_ids.filtered(
                lambda a: a.mimetype and a.mimetype.startswith('image/')
            )
            is_system = (
                m.message_type == 'notification'
                or text_body.startswith('Stage updated to:')
                or text_body.startswith('Artisan updated stage to:')
            )
            chat_messages.append({
                'id': m.id,
                'author': m.author_id.name or _('System'),
                'is_me': m.author_id.id == request.env.user.partner_id.id,
                'is_system': is_system,
                'time': m.date.strftime('%H:%M') if m.date else '',
                'body': text_body,
                'images': img_attachments,
            })

        return request.render('adaptfit_apparel.artisan_chat_detail_template', {
            'order': order,
            'order_cards': self._get_order_cards(),
            'garment_label': dict(order._fields['garment_type'].selection).get(order.garment_type, ''),
            'port_label': dict(order._fields['port_location'].selection).get(order.port_location, '') if order.port_location else '',
            'chat_messages': chat_messages,
            'artisan_user': request.env.user,
        })

    @http.route('/adaptfit/artisan/<int:order_id>/message', type='http', auth='user', methods=['POST'], website=False)
    def artisan_chat_post_message(self, order_id, body='', photo=None, **kwargs):
        order = request.env['adaptive.order'].browse(order_id).exists()
        if not order:
            return request.redirect('/adaptfit/artisan')

        attachments = []
        if photo and hasattr(photo, 'read'):
            raw = photo.read()
            if raw:
                attachments.append((photo.filename or 'seam_photo.jpg', raw))

        msg = False
        if body.strip() or attachments:
            msg = order.message_post(
                body=body.strip() or _('Workshop photo uploaded'),
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                attachments=attachments,
            )

        if self._is_ajax(**kwargs):
            payload = {'ok': bool(msg)}
            if msg:
                payload['message'] = self._serialize_message(msg, is_system=False)
            return request.make_json_response(payload)

        return request.redirect(f'/adaptfit/artisan/{order.id}')

    @http.route('/adaptfit/artisan/<int:order_id>/stage', type='http', auth='user', methods=['POST'], website=False)
    def artisan_chat_update_stage(self, order_id, target_state='', **kwargs):
        order = request.env['adaptive.order'].browse(order_id).exists()
        if not order:
            return request.redirect('/adaptfit/artisan')

        allowed = {
            'draft': _('Intake & Sizing'),
            'pattern': _('Cutting Started'),
            'stitching': _('Assembly / Sewing In Progress'),
            'transit': _('Ready for Clinic Transit'),
        }
        msg = False
        if target_state in allowed and order.state != target_state:
            order.write({'state': target_state})
            msg = order.message_post(
                body=_("Stage updated to: %s") % allowed[target_state],
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

        if self._is_ajax(**kwargs):
            payload = {'ok': True, 'state': order.state}
            if msg:
                payload['message'] = self._serialize_message(msg, is_system=True)
            return request.make_json_response(payload)

        return request.redirect(f'/adaptfit/artisan/{order.id}')
