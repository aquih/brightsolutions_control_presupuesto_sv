from typing import List, Tuple, NamedTuple
from collections import defaultdict
from logging import getLogger
from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = getLogger('********************************')


class ProductCostInfo(NamedTuple):
    sku: str
    total_cost: float
    total_max: float

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    sale_order_id = fields.Many2one('sale.order', string='Pedido de venta asoc.', domain=[('state', 'in', ['sale','done'])])

    def group_costs_by_product_sku(self):
        res = defaultdict(lambda: 0)

        for rec in self:
            for pol_id in rec.order_line:
                res[pol_id.product_id.default_code or pol_id.product_id.name] += pol_id.price_subtotal
        
        return res
    
    def action_open_pending_auth_lines(self):
        pol_ids = self.order_line.filtered(lambda ol: ol.auth_state == 'pendiente')
        return {
            'name': 'Lineas por autorizar',
            'view_mode': 'list',
            'res_model': 'purchase.order.line',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('id', 'in', pol_ids.ids)],
        }

    def button_confirm(self):
        if self.check_so():
            return self.check_so()
        super().button_confirm()

    def action_rfq_send(self):
        if self.check_so():
            return self.check_so()
        return super().action_rfq_send()

    def check_so(self):
        if self.sale_order_id:
            costs_info, unauth_pol_ids = self.check_costs()

            if unauth_pol_ids:
                costs_rows = []
                for p in costs_info:
                    row_class = auth_msg = ''
                    
                    if p.sku not in unauth_pol_ids.mapped('product_id.default_code') and p.sku not in unauth_pol_ids.mapped('product_id.name'):
                        auth_msg = '(Autorizado)'
                        row_class = 'table-success'

                    costs_rows.append(f"""
                        <tr class="{row_class}">
                            <td>{p.sku} {auth_msg}</td>
                            <td>{self.currency_id.symbol} {p.total_cost}</td>
                            <td>{self.currency_id.symbol} {p.total_max}</td>
                        </tr>
                    """)
                details_html = self.get_po_details_html()

                return {
                    'name': 'Lineas no permitidas',
                    'view_mode': 'form',
                    'res_model': 'auth.popup.wz',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': {
                        'default_purchase_line_ids': unauth_pol_ids.ids,
                        'default_msg': f"""
                            <div class="alert alert-info">
                                <i class="fa fa-info-circle mr-2"></i>
                                Los siguientes SKUs superan los montos definidos en la orden de venta asociada
                            </div>

                            <table class="table table-sm table-bordered">
                                <thead class="table-info">
                                    <tr>
                                        <th scope="col">SKU</th>
                                        <th scope="col">Costo total</th>
                                        <th scope="col">Costo maximo permitido</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {''.join(costs_rows)}
                                </tbody>
                            </table>
                        """,
                        'default_details': f"""{details_html}"""
                    }
                }


    def check_costs(self) -> Tuple[List[ProductCostInfo], 'PurchaseOrderLine']:

        res = []

        po_ids = self | self.search([('state', 'in', ['done','purchase']), ('sale_order_id', '=', self.sale_order_id.id)]) # quito este check ('id','=',self.id)

        sale_order_costs = self.sale_order_id.group_costs_by_product_sku()
        purchase_orders_costs = po_ids.group_costs_by_product_sku()

        products_not_found = [
            product_sku for product_sku in purchase_orders_costs 
            if product_sku not in sale_order_costs
        ]

        if products_not_found:
            raise ValidationError(f'Productos no encontrados en la orden de venta: {products_not_found}')

        for product_sku, auth_total_cost in sale_order_costs.items():
            if purchase_orders_costs[product_sku] > auth_total_cost:
                res.append(ProductCostInfo(product_sku, purchase_orders_costs[product_sku], auth_total_cost ))

        skus = [p.sku for p in res]
        unauth_pol_ids = False
        if skus:
            unauth_pol_ids = self.order_line.filtered(
                lambda ol: ol.auth_state != 'autorizado' and (ol.product_id.default_code if ol.product_id.default_code else ol.product_id.name in skus)
                # lambda ol: ol.auth_state != 'autorizado' and (ol.product_id.name in skus)
            )
        return res, unauth_pol_ids

    def get_po_details_html(self):
        po_ids = self | self.search([('state', 'in', ['done', 'purchase']), ('sale_order_id', '=', self.sale_order_id.id)])
        sale_order_costs = self.sale_order_id.group_costs_by_product_sku()
        _logger.info(sale_order_costs)
        rows_by_product = {}

        for po in po_ids:
            for line in po.order_line:
                sku = line.product_id.default_code or line.product_id.name
                if sku not in rows_by_product:
                    rows_by_product[sku] = {
                        'lines': [],
                        'total': 0.0,
                        'currency': po.currency_id.symbol
                    }
                rows_by_product[sku]['lines'].append({
                    'po_name': po.name,
                    'po_id': po.id,
                    'amount': line.price_subtotal
                })
                rows_by_product[sku]['total'] += line.price_subtotal

        html_parts = []

        for sku, data in rows_by_product.items():
            auth_total = sale_order_costs.get(sku, 0.0)
            total_used = data['total']
            difference = auth_total - total_used
            currency = data['currency']

            html_parts.append(f"""
                <div style="margin-top:20px;">
                    <h3> Producto {sku} </h3>
                    <table class="table table-sm table-bordered">
                        <thead class="table-info">
                            <tr>
                                <th>Nº PO</th>
                                <th>Monto producto</th>
                            </tr>
                        </thead>
                        <tbody>
            """)
            for line in data['lines']:
                link = f'<a href="/web#id={line["po_id"]}&model=purchase.order&view_type=form" target="_blank">{line["po_name"]}</a>'
                html_parts.append(f"""
                    <tr>
                        <td>{link}</td>
                        <td>{currency} {line["amount"]:.2f}</td>
                    </tr>
                """)

            html_parts.append(f"""
                        </tbody>
                    </table>
                    <div style="margin-top:5px;">
                        <strong>Total Restante (Sin Iva):</strong> {currency} {difference:.2f}
                    </div>
                </div>
            """)

        return ''.join(html_parts)

    def button_cancel(self):
        for line in self.order_line:
            line.write({'state': 'cancel'})
        super(PurchaseOrder,self).button_cancel()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'


    request_auth = fields.Boolean(string='Solicitar autorizacion', default=False)
    auth_state = fields.Selection(
        [('pendiente', 'Pendiente'), ('autorizado', 'Autorizado')],
        string='Estado de autorizacion',
        default=False,
    )

    def write(self, vals):
        for rec in self:
            if 'auth_state' not in vals and rec.auth_state == 'autorizado':
                raise ValidationError(f'Producto {rec.product_id.display_name}: No puede modificar una linea que ya está autorizada!')
        
        return super().write(vals)
    
    def unlink(self):
        if self.auth_state == 'autorizado' and not self.env.user.has_group('brightsolutions_control_presupuesto.group_purchase_lines_auth'):
            raise ValidationError('No puede eliminar lineas autorizadas. Requiere permisos de usuario autorizador')

        return super().unlink()

    def btn_auth(self):
        self.write({'auth_state': 'autorizado'})
