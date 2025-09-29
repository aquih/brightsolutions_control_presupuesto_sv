from collections import defaultdict
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def group_costs_by_product_sku(self):
        res = defaultdict(lambda: 0)

        for sol_id in self.order_line:
            res[sol_id.product_id.product_variant_id.default_code or sol_id.product_id.product_variant_id.name] += sol_id.costo_total
        
        return res