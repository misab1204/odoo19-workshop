# -*- coding: utf-8 -*-
import base64
from odoo import http, _
from odoo.http import request
from odoo.tools import html2plaintext


class ArtisanChatController(http.Controller):

    @http.route('/adaptfit/artisan', type='http', auth='user', website=False)
    def artisan_chat_list(self, **kwargs):
        orders = request.env['adaptive.order'].search([
            ('state', 'in', ('draft', 'pattern', 'stitching', 'transit')),
        ], order='urgency_level desc, create_date desc')

        order_cards = []
        for o in orders:
            last_msg = o.message_ids.filtered(lambda m: m.message_type in ('comment', 'email') and m.body)[:1]
            preview = html2plaintext(last_msg.body).strip()[:65] if last_msg else _("Ready for workshop review")
            order_cards.append({
                'order': o,
                'garment_label': dict(o._fields['garment_type'].selection).get(o.garment_type, ''),
                'state_label': dict(o._fields['state'].selection).get(o.state, ''),
                'preview': preview,
            })

        return request.render('adaptfit_apparel.artisan_chat_list_template', {
            'order_cards': order_cards,
            'artisan_user': request.env.user,
        })

    @http.route('/adaptfit/artisan/<int:order_id>', type='http', auth='user', website=False)
    def artisan_chat_detail(self, order_id, **kwargs):
        order = request.env['adaptive.order'].browse(order_id).exists()
        if not order:
            return request.redirect('/adaptfit/artisan')

        messages = order.message_ids.filtered(
            lambda m: m.message_type in ('comment', 'notification', 'email') and (m.body or m.attachment_ids)
        ).sorted(key=lambda m: m.date)

        chat_messages = []
        for m in messages:
            text_body = html2plaintext(m.body or '').strip()
            img_attachments = m.attachment_ids.filtered(lambda a: a.mimetype and a.mimetype.startswith('image/'))
            chat_messages.append({
                'id': m.id,
                'author': m.author_id.name or _('System'),
                'is_me': m.author_id.id == request.env.user.partner_id.id,
                'time': m.date.strftime('%H:%M') if m.date else '',
                'body': text_body,
                'images': img_attachments,
            })

        return request.render('adaptfit_apparel.artisan_chat_detail_template', {
            'order': order,
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

        if body.strip() or attachments:
            order.message_post(
                body=body.strip() or _('📷 Workshop photo uploaded'),
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                attachments=attachments,
            )

        return request.redirect(f'/adaptfit/artisan/{order.id}')

    @http.route('/adaptfit/artisan/<int:order_id>/stage', type='http', auth='user', methods=['POST'], website=False)
    def artisan_chat_update_stage(self, order_id, target_state='', **kwargs):
        order = request.env['adaptive.order'].browse(order_id).exists()
        if not order:
            return request.redirect('/adaptfit/artisan')

        allowed = {
            'pattern': _('✂️ Cutting Started'),
            'stitching': _('🧵 Assembly / Sewing In Progress'),
            'transit': _('📦 Ready for Clinic Transit'),
        }
        if target_state in allowed:
            order.write({'state': target_state})
            order.message_post(
                body=_("Artisan updated stage to: %s") % allowed[target_state],
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

        return request.redirect(f'/adaptfit/artisan/{order.id}')
