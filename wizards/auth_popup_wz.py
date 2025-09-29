from odoo import fields, models


class AuthPopupWz(models.TransientModel):
    _name = 'auth.popup.wz'

    msg = fields.Html(readonly=True, store=True)
    details = fields.Html(readonly=True, store=True)
    purchase_line_ids = fields.Many2many('purchase.order.line', string='Lineas a autorizar')

    def btn_ok(self):
        self.purchase_line_ids.filtered('request_auth').write({'auth_state': 'pendiente'})