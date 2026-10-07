from odoo import api, fields, models
from odoo.exceptions import ValidationError
import copy
from logging import getLogger
import requests
from requests.auth import HTTPBasicAuth
import json
_logger = getLogger(__name__)
from random import randint
from odoo.addons.odoosync_base.utils.app_delivery import AppDelivery


class MycarrierLocationType(models.Model):
    _name = "mycarrier.location.type"
    _description = "MyCarrier Location Type"

    _order = 'sequence DESC'

    name = fields.Char(string='Name', required=True, copy=False)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Location Type already exists !"),
    ]


class MycarrierInstance(models.Model):
    _name = 'mycarrier.instance'
    _description = 'MyCarrier Instance'

    name = fields.Char('Instance Name')
    token = fields.Char('Service Key')
    account_id = fields.Many2one(
        string='Linked Account',
        comodel_name='omni.account',
        ondelete='restrict',
    )
    connect_state = fields.Selection([
        ('draft', 'Failed'),
        ('confirm', 'Confirmed')],
        default='draft', string='State')

    product_mapping_ids = fields.One2many('mycarrier.product.mappings', inverse_name='mycarrier_instance_id')
    registered_webhook_ids = fields.One2many('mycarrier.registered.webhooks', inverse_name='mycarrier_instance_id')

    delivery_product_id = fields.Many2one(
        comodel_name='product.product',
        string='Delivery Product',
        domain=[('type', '=', 'service')],
        help="""Delivery product used for shipping method creation.""",
    )

    location_source = fields.Selection([
        ('warehouse', 'Warehouse'),
        ('location', 'Location')],
        string='Location ID Source', default='warehouse', required=True,
        help="Where the origin locationID sent to MyCarrier comes from:\n"
             "Warehouse: looked up in the Warehouse Mapping tab by the picking's warehouse.\n"
             "Location: looked up in the Location Mapping tab by the picking's source location.")

    warehouse_mapping_ids = fields.One2many('mycarrier.warehouse.mappings', inverse_name='mycarrier_instance_id')
    location_mapping_ids = fields.One2many('mycarrier.location.mappings', inverse_name='mycarrier_instance_id')

    quote_build_mode = fields.Selection([
        ('product', 'Product-wise (per product line, grouped by Package Type)'),
        ('package', 'Package-wise (per package)')],
        string='Quote Build Mode', default='product', required=True,
        help="Product-wise: same-Package-Type packages are aggregated into one quoteUnit; "
             "one quoteCommodity per product line, weight/class/NMFC/NMFC Sub taken from the "
             "product.\n"
             "Package-wise: one quoteUnit and one quoteCommodity per package, never "
             "aggregated - the whole pallet is one freight line. Commodity Description is the "
             "package reference; weight, class, NMFC and NMFC Sub are taken from the package "
             "itself (its Shipping Weight and the MyCarrier fields on the package form).")

    auto_validate_picking = fields.Boolean(
        'Auto-Validate Picking on MyCarrier Confirmation', default=True,
        help="When MyCarrier's webhook confirms a shipment, automatically validate the picking. "
             "If off, the webhook still fills in PRO/BOL/cost and logs the update, but leaves "
             "the picking for manual validation.")

    auto_validate_timing = fields.Selection([
        ('immediate', 'Immediately on Confirmation'),
        ('pickup_date', 'Wait Until Pickup Date')],
        string='Validate Timing', default='pickup_date', required=True,
        help="Immediately: validate as soon as MyCarrier confirms the shipment.\n"
             "Wait Until Pickup Date: hold off validating until the confirmed PickupDate "
             "has actually arrived (matches physical pickup, but the picking sits in "
             "'MyCarrier' state until then). Client's call - confirm before go-live.")

    default_origin_location_type = fields.Many2one('mycarrier.location.type', string='Origin Location Type')
    default_dest_location_type = fields.Many2one('mycarrier.location.type', string='Destination Location Type')
    default_origin_inside_pickup = fields.Boolean('Inside Pickup')
    default_origin_liftgate_pickup = fields.Boolean('Liftgate Pickup')
    default_origin_protect_from_freeze = fields.Boolean('Protect From Freeze')
    default_origin_single_shipment = fields.Boolean('Single Shipment')
    default_origin_inbond_freight = fields.Boolean('In Bond Freight')
    default_dest_delivery_appointment = fields.Boolean('Delivery Appointment')
    default_dest_inside_delivery = fields.Boolean('Inside Delivery')
    default_dest_liftgate_delivery = fields.Boolean('Liftgate Delivery')
    default_dest_notify_delivery = fields.Boolean('Notify Before Delivery')
    default_dest_sort_segregate_delivery = fields.Boolean('Sort/Segregate Delivery')

    def check_connection_access(self):
        self.registered_webhook_ids.unlink()
        res = self.get_webhook()
        if res:
            self.connect_state = 'confirm'

    def _get_quote_build_mode(self):
        """Read directly, no caching - Odoo's registry cache only supports a fixed set of
        shared bucket names (no way for an addon to register its own independently-clearable
        bucket), so caching this would mean clearing the shared 'default' bucket on every
        write here, touching every other module's cached methods too. The query itself is a
        single indexed lookup against a table with a handful of rows - cheap enough even at
        the frequency this is called (every product/package form open) that it's not worth
        that tradeoff."""
        instance = self.search([('connect_state', '=', 'confirm')], limit=1)
        return instance.quote_build_mode or 'product'

    def get_origin_location_id(self, picking):
        self.ensure_one()
        if self.location_source == 'location':
            mapping = self.location_mapping_ids.filtered(lambda l: l.location_id == picking.location_id)
        else:
            mapping = self.warehouse_mapping_ids.filtered(
                lambda l: l.warehouse_id == picking.picking_type_id.warehouse_id)
        return mapping[:1].mycarrier_location_id or ''

    def create_quote(self, data):
        if not self.token:
            raise ValidationError('MyCarrier instance "%s" has no Service Key configured.' % self.name)
        payload = {
            "orders": [
                {
                    "carrier": "",
                    "carrierService": "",
                    "destinationAccessorials": data['destinationAccessorials'],
                    "destinationStop": data['destinationStop'],
                    "emergencyContactPersonName": "",
                    "emergencyContactPhone": "",
                    "isVicsBol": "",
                    "originAccessorials": data['originAccessorials'],
                    "originStop": {
                        "city": "",
                        "closeTime": "",
                        "companyName": "",
                        "contactEmail": "",
                        "contactFirstName": "",
                        "contactLastName": "",
                        "contactPhone": "",
                        "country": "",
                        "ext": "",
                        "instructions": "",
                        "locationID": data.get('origin_location_id', ''),
                        "locationType": data['origin_location_type'] or "Business",
                        "readyTime": "",
                        "state": "",
                        "streetLine1": "",
                        "streetLine2": "",
                        "zip": ""
                    },
                    "paymentDirection": "Prepaid",
                    "pickupDate": data['pickupDate'],
                    "proNumber": "",
                    "quoteReferenceID": data['quoteReferenceID'],
                    "quoteUnits": data['quoteUnits'],
                    "readyToDispatch": "N",
                    "references": data['references'],
                    "serviceType": "LTL",
                    "specialInstructions": data.get('special_instructions', ''),
                    # "timeCreated": "01:13:24",
                    "vicsBolPrefix": ""
                }
            ]
        }
        srm = AppDelivery(service_name='mycarrier', service_type='create_quote', service_key=self.token)
        srm.data = payload
        response = srm.create_quote(debug_logging=self.account_id.debug_logging, company_id=self.account_id.company_id.id)
        if response.get('isSuccess'):
            return True
        error_message = (
            response.get('errors') or response.get('errorMessage')
            or response.get('message') or response.get('Message') or response
        )
        raise ValidationError('MyCarrier rejected the quote: %s' % error_message)


    def get_webhook(self):
        srm = AppDelivery(service_name='mycarrier', service_type='get_webhook_info', service_key=self.token)
        data = srm.get_webhooks(debug_logging=self.account_id.debug_logging, company_id=self.account_id.company_id.id)
        if data:
            for webhook in data:
                webhook_id = self.env['mycarrier.registered.webhooks'].create({
                    'webhook_environment': webhook.get('environment'),
                    'webhook_username': webhook.get('credentialUserName'),
                    'webhook_customerid': str(webhook.get('customerId')),
                    'webhook_type': webhook.get('webhookType'),
                    'webhook_uri': webhook.get('uri'),
                    'mycarrier_instance_id': self.id
                })
            return True


class MycarrierWarehouseMappings(models.Model):
    _name = 'mycarrier.warehouse.mappings'
    _description = 'MyCarrier Warehouse Mappings'

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    mycarrier_location_id = fields.Char(string='MyCarrier Location ID', required=True)
    mycarrier_instance_id = fields.Many2one('mycarrier.instance')

    _sql_constraints = [
        ('warehouse_uniq', 'unique (warehouse_id, mycarrier_instance_id)', "Warehouse must be unique.")
    ]


class MycarrierLocationMappings(models.Model):
    _name = 'mycarrier.location.mappings'
    _description = 'MyCarrier Location Mappings'

    location_id = fields.Many2one('stock.location', string='Location', required=True)
    mycarrier_location_id = fields.Char(string='MyCarrier Location ID', required=True)
    mycarrier_instance_id = fields.Many2one('mycarrier.instance')

    _sql_constraints = [
        ('location_uniq', 'unique (location_id, mycarrier_instance_id)', "Location must be unique.")
    ]


class MycarrierRegisteredWebhook(models.Model):
    _name = 'mycarrier.registered.webhooks'
    _description = 'MyCarrier Register Webhooks'

    webhook_environment = fields.Char('Environment')
    webhook_username = fields.Char('Credential UserName')
    webhook_customerid = fields.Char('CustomerID')
    webhook_type = fields.Char('Webhook Type')
    webhook_uri = fields.Char('URI')
    mycarrier_instance_id = fields.Many2one('mycarrier.instance')


class MycarrierAccessorials(models.Model):
    _name = "mycarrier.accessorials"
    _description = "MyCarrier Accessorials"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Accessorial', required=True)
    color = fields.Integer('Color', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Accessorial already exists !"),
    ]


