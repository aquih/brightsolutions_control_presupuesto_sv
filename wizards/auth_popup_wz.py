from odoo import api, fields, models

class AuthPopupWz(models.TransientModel):
    _name = 'auth.popup.wz'

    msg = fields.Html(readonly=True, store=True)
    details = fields.Html(readonly=True, store=True)
    purchase_line_ids = fields.Many2many('purchase.order.line', string='Lineas a autorizar')
    
    @api.onchange('purchase_line_ids')
    def _onchange_purchase_line_ids(self):
        purchase_order = self.purchase_line_ids[0]._origin.order_id
        lineas_reales_ids = [l._origin.id for l in self.purchase_line_ids]
        lineas_activas_ids = [l._origin.id for l in self.purchase_line_ids.filtered('request_auth')]
        
        lineas_actualizadas = []
        for line_id in lineas_reales_ids:
            toggle_value = line_id in lineas_activas_ids
            if toggle_value == True:
                lineas_actualizadas.append((1, line_id, {'auth_state': 'pendiente', 'request_auth': toggle_value}))
            else:
                lineas_actualizadas.append((1, line_id, {'auth_state': None, 'request_auth': toggle_value}))

        purchase_order.write({
            'order_line': lineas_actualizadas
        })

    def btn_ok(self):
        return {'type': 'ir.actions.act_window_close'}