from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    weight_done = fields.Float(compute='_cal_move_weight_done', digits='Stock Weight', compute_sudo=True)

    @api.depends('product_id', 'quantity', 'product_id.weight')
    def _cal_move_weight_done(self):
        moves_with_weight = self.filtered(lambda moves: moves.product_id.weight > 0.00)
        for move in moves_with_weight:
            move.weight_done = move.quantity * move.product_id.weight
        (self - moves_with_weight).weight_done = 0
