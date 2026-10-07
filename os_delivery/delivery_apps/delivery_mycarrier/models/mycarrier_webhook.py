import json
from odoo import models, fields, api, exceptions, _
import ast
import logging
import requests
from markupsafe import Markup, escape
from datetime import datetime
_logger = logging.getLogger(__name__)


def _format_mycarrier_price_breakdown_html(payload):
    """Build HTML cost breakdown from MyCarrier's ShipmentPriceDetails."""
    price_details = payload.get('ShipmentPriceDetails') or []
    if not price_details:
        return Markup("")
    li = "".join(
        "<li>%s: $%s</li>" % (escape(item.get('Description', '')), escape(item.get('Amount', '')))
        for item in price_details
    )
    total = payload.get('TotalCost')
    total_line = Markup("")
    if total is not None:
        total_line = Markup("<li><b>%s: $%s</b></li>") % (escape(_("Total")), escape(total))
    return Markup("<div><b>%s</b><ul>%s%s</ul></div>") % (escape(_("Cost breakdown")), Markup(li), total_line)


def _download_mycarrier_file(url):
    if not url:
        return None
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.content
        _logger.warning('MyCarrier file download failed (status %s) for %s', response.status_code, url)
    except Exception as e:
        _logger.warning('MyCarrier file download failed for %s: %s', url, e)
    return None


class MycarrierWebhook(models.Model):
    _name = 'mycarrier.webhook'
    _description = 'MyCarrier Webhook'
    _order = 'id desc'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('mycarrier.webhook'))
    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'), ('done', 'Done'), ('error', 'Error')],
        default='draft',
    )
    data = fields.Char('Data')

    def _process_data(self):
        for record in self:
            picking_id = False
            try:
                # json_str = json.dumps(record.data)
                data = ast.literal_eval(record.data)
                message = data['Message']
                payload = data['Payload']
                _logger.info(data)
                picking_id = self.env['stock.picking'].search([('name', '=', payload['ReferenceNumber']), ('state', '=', 'mycarrier')])
                if picking_id:
                    # picking_id.message_post(body=message)
                    picking_id.write({
                        'mycarrier_shipment_id': payload['ShipmentId'],
                        'mycarrier_customer_bol_number': payload['CustomerBOLNumber'],
                        'mycarrier_po_number': payload['PONumber'],
                        'mycarrier_ref_number': payload['ReferenceNumber'],
                        'mycarrier_pickup_number': payload['PickupNumber'],
                        'mycarrier_carrier_code': payload['CarrierCode'],
                        'mycarrier_carrier_name': payload['CarrierName'],
                        'mycarrier_pro_number': payload['CarrierPRONumber'],
                        'mycarrier_total_cost': float(payload['TotalCost']),
                        'carrier_tracking_ref': payload['CarrierPRONumber'],
                        'mycarrier_pickup_date': payload['PickupDate'],
                        'mycarrier_transit_time': payload.get('TransitTime'),
                        'mycarrier_estimated_delivery_date': payload.get('EstimatedDeliveryDate'),
                    })
                    self._cr.commit()

                    logmessage = Markup("<b>%s</b><br/><br/>%s") % (
                        escape(_("Shipment confirmed by MyCarrier")),
                        Markup("<div>%s</div>") % Markup("<br/>").join([
                            Markup("<b>%s</b> %s") % (escape(_("PRO Number:")), escape(payload.get('CarrierPRONumber') or '')),
                            Markup("<b>%s</b> %s") % (escape(_("BOL Number:")), escape(payload.get('CustomerBOLNumber') or '')),
                            Markup("<b>%s</b> %s") % (escape(_("Carrier:")), escape(payload.get('CarrierName') or '')),
                        ]),
                    )
                    breakdown = _format_mycarrier_price_breakdown_html(payload)
                    if breakdown:
                        logmessage = Markup("%s<br/><br/>%s") % (logmessage, breakdown)

                    file_ref = payload.get('CarrierPRONumber') or payload.get('ShipmentId') or picking_id.name
                    attachments = []
                    bol_bytes = _download_mycarrier_file(payload.get('BOLLink'))
                    if bol_bytes:
                        attachments.append(('BOL-%s.pdf' % file_ref, bol_bytes))
                    label_bytes = _download_mycarrier_file(payload.get('LabelLink'))
                    if label_bytes:
                        attachments.append(('Label-%s.pdf' % file_ref, label_bytes))
                    picking_id.message_post(body=logmessage, attachments=attachments)

                    mycarrier_instance_id = self.env['mycarrier.instance'].search([('connect_state', '=', 'confirm')], limit=1)
                    carrier_id = self.env['delivery.carrier'].sudo().search(
                        [('mycarrier_carrier_code', '=', payload['CarrierCode'])], limit=1
                    )
                    if not carrier_id:
                        product_id = mycarrier_instance_id.delivery_product_id
                        if product_id:
                            carrier_id = self.env['delivery.carrier'].sudo().create({
                                'name': payload['CarrierName'],
                                'mycarrier_carrier_code': payload['CarrierCode'],
                                'fixed_price': 0,
                                'product_id': product_id.id
                            })
                    if carrier_id:
                        picking_id.carrier_id = carrier_id.id

                    if not mycarrier_instance_id.auto_validate_picking:
                        record.state = 'done'
                    elif mycarrier_instance_id.auto_validate_timing == 'pickup_date':
                        date_obj = datetime.strptime(payload['PickupDate'], '%m/%d/%Y %H:%M:%S').date()
                        if date_obj <= fields.Date.today():
                            res_dict = picking_id.button_validate()
                            if type(res_dict) != bool:
                                self.env['stock.backorder.confirmation'].with_context(res_dict['context']).process()
                            record.state = 'done'
                        # else: leave as draft, retried by the cron once the pickup date arrives
                    else:
                        res_dict = picking_id.button_validate()
                        if type(res_dict) != bool:
                            self.env['stock.backorder.confirmation'].with_context(res_dict['context']).process()
                        record.state = 'done'
            except Exception as e:
                _logger.error(e)
                if picking_id:
                    picking_id.message_post(body=str(e))
                record.state = 'error'

    def _process_webhooks(self):
        records = self.search([('state', 'in', ['draft', 'error'])])
        records._process_data()
