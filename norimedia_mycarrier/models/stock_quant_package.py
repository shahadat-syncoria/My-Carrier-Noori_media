from odoo import api, fields, models


class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    def _set_mycarrier_package_count_from_cartons(self, vals):
        cartons = vals.get('pallet_cartons', '')
        if cartons:
            vals['mycarrier_package_count'] = len(
                [c for c in cartons.split(',') if c.strip()]
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'pallet_cartons' in vals:
                self._set_mycarrier_package_count_from_cartons(vals)
        return super().create(vals_list)

    def write(self, vals):
        if 'pallet_cartons' in vals:
            self._set_mycarrier_package_count_from_cartons(vals)
        return super().write(vals)
