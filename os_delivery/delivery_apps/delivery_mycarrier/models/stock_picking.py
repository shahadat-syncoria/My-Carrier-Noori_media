from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

MYCARRIER_SHIPPING_UNIT_TYPES = {
    'Bag', 'Bale', 'Box', 'Bucket', 'Bundle', 'Carton', 'Case', 'Crate', 'Cylinder',
    'Drums', 'Pail', 'Pallet', 'Pieces', 'Reel', 'Roll', 'Skid', 'Tote', 'Tube',
}


def _default_from_mycarrier_instance(instance_field_name):
    """Default an accessorial boolean or location type from the confirmed mycarrier.instance's
    own default - only applied at record creation, so it's just a starting value the user can
    still change freely on the picking afterward."""
    def _default(self):
        instance = self.env['mycarrier.instance'].search([('connect_state', '=', 'confirm')], limit=1)
        if not instance:
            return False
        value = instance[instance_field_name]
        return value.id if hasattr(value, 'id') else bool(value)
    return _default


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    dest_delivery_appointment = fields.Boolean(
        'Delivery Appointment', tracking=True,
        default=_default_from_mycarrier_instance('default_dest_delivery_appointment'))
    dest_inside_delivery = fields.Boolean(
        'Inside Delivery', tracking=True,
        default=_default_from_mycarrier_instance('default_dest_inside_delivery'))
    dest_liftgate_delivery = fields.Boolean(
        'Liftgate Delivery', tracking=True,
        default=_default_from_mycarrier_instance('default_dest_liftgate_delivery'))
    dest_notify_delivery = fields.Boolean(
        'Notify Before Delivery', tracking=True,
        default=_default_from_mycarrier_instance('default_dest_notify_delivery'))
    dest_sort_segregate_delivery = fields.Boolean(
        'Sort/Segregate Delivery', tracking=True,
        default=_default_from_mycarrier_instance('default_dest_sort_segregate_delivery'))
    dest_location_type = fields.Many2one(
        'mycarrier.location.type', string='Destination Location Type', tracking=True,
        default=_default_from_mycarrier_instance('default_dest_location_type'))

    origin_inbond_freight = fields.Boolean(
        'In Bond Freight', tracking=True,
        default=_default_from_mycarrier_instance('default_origin_inbond_freight'))
    origin_inside_pickup = fields.Boolean(
        'Inside Pickup', tracking=True,
        default=_default_from_mycarrier_instance('default_origin_inside_pickup'))
    origin_liftgate_pickup = fields.Boolean(
        'Liftgate Pickup', tracking=True,
        default=_default_from_mycarrier_instance('default_origin_liftgate_pickup'))
    origin_protect_from_freeze = fields.Boolean(
        'Protect From Freeze', tracking=True,
        default=_default_from_mycarrier_instance('default_origin_protect_from_freeze'))
    origin_single_shipment = fields.Boolean(
        'Single Shipment', tracking=True,
        default=_default_from_mycarrier_instance('default_origin_single_shipment'))
    origin_location_type = fields.Many2one(
        'mycarrier.location.type', string='Origin Location Type', tracking=True,
        default=_default_from_mycarrier_instance('default_origin_location_type'))

    total_weight_done = fields.Float(compute='_cal_total_weight_done', digits='Stock Weight', help="This field is for MyCarrier", compute_sudo=True, string='Total Weight Done')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('mycarrier', 'MyCarrier'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.")

    pushed_to_mycarrier = fields.Boolean('Pushed To MyCarrier', copy=False)

    mycarrier_shipment_id = fields.Char('ShipmentId', tracking=True, copy=False)
    mycarrier_customer_bol_number = fields.Char('CustomerBOLNumber', tracking=True, copy=False)
    mycarrier_po_number = fields.Char('PONumber', tracking=True, copy=False)
    mycarrier_ref_number = fields.Char('ReferenceNumber', tracking=True, copy=False)
    mycarrier_pickup_number = fields.Char('PickupNumber', tracking=True, copy=False)
    mycarrier_carrier_code = fields.Char('CarrierCode', tracking=True, copy=False)
    mycarrier_carrier_name = fields.Char('CarrierName', tracking=True, copy=False)
    mycarrier_pro_number = fields.Char('CarrierPRONumber', tracking=True, copy=False)
    mycarrier_total_cost = fields.Float('TotalCost', tracking=True, copy=False)
    mycarrier_pickup_date = fields.Char('Pickup Date', tracking=True, copy=False)
    mycarrier_transit_time = fields.Char('Transit Time (Days)', tracking=True, copy=False)
    mycarrier_estimated_delivery_date = fields.Char('Estimated Delivery Date', tracking=True, copy=False)
    mycarrier_special_instructions = fields.Text('Special Instructions')

    @api.depends('move_ids.weight_done')
    def _cal_total_weight_done(self):
        for picking in self:
            picking.total_weight_done = sum(move.weight_done for move in picking.move_ids)

    # Superseded by create_mycarrier_quote_by_package (package-wise quoting).
    # Kept commented for reference, not wired to any button/action - unused, no live callers.
    # def create_mycarrier_quote(self):
    #     self.ensure_one()
    #     if self.state == 'mycarrier':
    #         self.message_post(body='Update to MyCarrier')
    #     mycarrier_instance = self.env['mycarrier.instance'].search([('connect_state', '=', 'confirm')], limit=1)
    #     if not mycarrier_instance:
    #         raise ValidationError('No MyCarrier Instance Found')
    #     name_arr = self.partner_id.name.split()
    #     last_name = name_arr.pop()
    #     first_name = ' '.join(name_arr)
    #     phone_number = self.partner_id.phone or self.partner_id.mobile or ''
    #     formatted_phone = phone_number
    #     if '+1' in phone_number:
    #         formatted_phone = phone_number.replace('+1', '')
    #     data = {
    #         'destinationStop': {
    #             'city': self.partner_id.city or '',
    #             "closeTime": "",
    #             'companyName': self.partner_id.parent_id.name if self.partner_id.parent_id else self.partner_id.name,
    #             'contactEmail': self.partner_id.email or '',
    #             "contactFirstName": first_name or '',
    #             "contactLastName": last_name or '',
    #             'contactPhone': formatted_phone,
    #             'country': self.partner_id.country_id.code or '',
    #             "ext": "",
    #             "instructions": "",
    #             "locationID": "",
    #             'locationType': self.dest_location_type.name,
    #             "readyTime": "",
    #             'state': self.partner_id.state_id.code or '',
    #             'streetLine1': self.partner_id.street or '',
    #             'streetLine2': self.partner_id.street2 or '',
    #             'zip': self.partner_id.zip or '',
    #         },
    #         'destinationAccessorials': {
    #             'deliveryAppointment': "true" if self.dest_delivery_appointment else "false",
    #             'insideDelivery': "true" if self.dest_inside_delivery else "false",
    #             'liftgateDelivery': "true" if self.dest_liftgate_delivery else "false",
    #             'notifyBeforeDelivery': "true" if self.dest_notify_delivery else "false",
    #             'sortOrSegregateDelivery': "true" if self.dest_sort_segregate_delivery else "false"
    #         },
    #         'originAccessorials': {
    #             'inBondFreight': "true" if self.origin_inbond_freight else "false",
    #             'insidePickup': "true" if self.origin_inside_pickup else "false",
    #             'liftgatePickup': "true" if self.origin_liftgate_pickup else "false",
    #             'protectFromFreeze': "true" if self.origin_protect_from_freeze else "false",
    #             'singleShipment': "true" if self.origin_single_shipment else "false"
    #         },
    #         'quoteReferenceID': self.name,
    #         'pickupDate': fields.Date.from_string(self.scheduled_date).strftime('%m/%d/%Y'),
    #         'references': {
    #             "poNumber": '',
    #             "referenceNumber": self.name or ''
    #         },
    #         'origin_location_type': self.origin_location_type.name
    #     }
    #     units = []
    #     extra_weight = 0
    #     extra_pieces = 0
    #     product_ids = mycarrier_instance.product_mapping_ids.mapped('product_id')
    #     for move in self.move_ids.filtered(lambda m: m.quantity > 0):
    #         if move.product_id not in product_ids:
    #             extra_pieces += move.quantity
    #             extra_weight += move.weight_done
    #     for move in self.move_ids.filtered(lambda m: m.quantity > 0):
    #         if move.product_id in product_ids:
    #             prod_id = mycarrier_instance.product_mapping_ids.filtered(lambda l: l.product_id == move.product_id)
    #             units.append(
    #                 {
    #                     "quoteCommodities": [
    #                         {
    #                             "commodityClass": "",
    #                             "commodityDescription": "",
    #                             "commodityHazMat": "",
    #                             "commodityNMFC": "",
    #                             "commodityPackingType": "",
    #                             "commodityPieces": int(move.quantity),
    #                             "commoditySub": "",
    #                             "commodityWeight": int(move.weight_done),
    #                             "customerOrderNumber": "",
    #                             "hazmatHazardClass": "",
    #                             "hazmatIDNumber": "",
    #                             "hazmatPackingGroup": "",
    #                             "hazmatProperShippingName": "",
    #                             "productID": prod_id.mycarrier_product_id
    #                         }
    #                     ],
    #                     "shippingUnitCount": int(move.quantity),
    #                     "shippingUnitType": "",
    #                     "unitHeight": "",
    #                     "unitLength": "",
    #                     "unitStackable": False,
    #                     "unitWidth": ""
    #                 }
    #             )
    #     if len(units) > 0:
    #         _logger.info(units)
    #         units[0]['quoteCommodities'][0]['commodityPieces'] += int(extra_pieces)
    #         units[0]['quoteCommodities'][0]['commodityWeight'] += int(extra_weight)
    #     else:
    #         raise ValidationError('Need at least one product on MyCarrier Product List')
    #     data['quoteUnits'] = units
    #
    #     if mycarrier_instance:
    #         mycarrier_instance.create_quote(data)
    #         self.pushed_to_mycarrier = True
    #         self.state = 'mycarrier'

    def create_mycarrier_quote_by_package(self):
        """Package-wise quote build: one quoteUnit per stock.quant.package,
        one quoteCommodities entry per product line inside that package."""
        self.ensure_one()
        if self.state == 'mycarrier':
            self.message_post(body='Update to MyCarrier')
        mycarrier_instance = self.env['mycarrier.instance'].search([('connect_state', '=', 'confirm')], limit=1)
        if not mycarrier_instance:
            raise ValidationError('No MyCarrier Instance Found')
        if not self.partner_id:
            raise ValidationError(f'{self.name} has no Customer set. Set a Customer before sending to MyCarrier.')
        name_arr = self.partner_id.name.split()
        last_name = name_arr.pop()
        first_name = ' '.join(name_arr)
        phone_number = self.partner_id.phone or self.partner_id.mobile or ''
        formatted_phone = phone_number
        if '+1' in phone_number:
            formatted_phone = phone_number.replace('+1', '')
        data = {
            'destinationStop': {
                'city': self.partner_id.city or '',
                "closeTime": "",
                'companyName': self.partner_id.parent_id.name if self.partner_id.parent_id else self.partner_id.name,
                'contactEmail': self.partner_id.email or '',
                "contactFirstName": first_name or '',
                "contactLastName": last_name or '',
                'contactPhone': formatted_phone,
                'country': self.partner_id.country_id.code or '',
                "ext": "",
                "instructions": "",
                "locationID": "",
                'locationType': self.dest_location_type.name,
                "readyTime": "",
                'state': self.partner_id.state_id.code or '',
                'streetLine1': self.partner_id.street or '',
                'streetLine2': self.partner_id.street2 or '',
                'zip': self.partner_id.zip or '',
            },
            'destinationAccessorials': {
                'deliveryAppointment': "true" if self.dest_delivery_appointment else "false",
                'insideDelivery': "true" if self.dest_inside_delivery else "false",
                'liftgateDelivery': "true" if self.dest_liftgate_delivery else "false",
                'notifyBeforeDelivery': "true" if self.dest_notify_delivery else "false",
                'sortOrSegregateDelivery': "true" if self.dest_sort_segregate_delivery else "false"
            },
            'originAccessorials': {
                'inBondFreight': "true" if self.origin_inbond_freight else "false",
                'insidePickup': "true" if self.origin_inside_pickup else "false",
                'liftgatePickup': "true" if self.origin_liftgate_pickup else "false",
                'protectFromFreeze': "true" if self.origin_protect_from_freeze else "false",
                'singleShipment': "true" if self.origin_single_shipment else "false"
            },
            'quoteReferenceID': self.name,
            'pickupDate': fields.Date.from_string(self.scheduled_date).strftime('%m/%d/%Y'),
            'references': {
                "poNumber": self.mycarrier_po_number or '',
                "referenceNumber": self.name or '',
                "customerBOLNumber": self.mycarrier_customer_bol_number or '',
            },
            'origin_location_type': self.origin_location_type.name,
            'origin_location_id': mycarrier_instance.get_origin_location_id(self),
            'special_instructions': self.mycarrier_special_instructions or '',
        }

        if mycarrier_instance.quote_build_mode == 'package':
            units = self._build_quote_units_package_wise()
        else:
            units = self._build_quote_units_product_wise(mycarrier_instance)
        if not units:
            raise ValidationError('Need at least one package with products to send to MyCarrier')
        data['quoteUnits'] = units

        mycarrier_instance.create_quote(data)
        self.pushed_to_mycarrier = True
        self.state = 'mycarrier'

    def _validate_mycarrier_package(self, package):
        if not package.package_type_id:
            raise ValidationError(f'Package {package.name} has no Package Type set. Set a Package Type before sending to MyCarrier.')
        if not (package.package_type_id.height and package.package_type_id.packaging_length and package.package_type_id.width):
            raise ValidationError(
                f'Package Type "{package.package_type_id.name}" (used on package {package.name}) is missing '
                'Height/Length/Width. MyCarrier requires all three dimensions. Set them on the Package Type.')
        if package.package_type_id.name not in MYCARRIER_SHIPPING_UNIT_TYPES:
            raise ValidationError(
                f'Package Type "{package.package_type_id.name}" (used on package {package.name}) is not a valid '
                f'MyCarrier shipping unit type. Rename it to one of: {", ".join(sorted(MYCARRIER_SHIPPING_UNIT_TYPES))}.')

    def _build_quote_units_product_wise(self, mycarrier_instance):
        """Product-wise mode: packages grouped by Package Type (same-type packages
        aggregated into one quoteUnit), one quoteCommodities entry per product line."""
        product_ids = mycarrier_instance.product_mapping_ids.mapped('product_id')
        packages = self.move_line_ids.mapped('result_package_id')
        for package in packages:
            self._validate_mycarrier_package(package)

        packages_by_type = {}
        for package in packages:
            packages_by_type.setdefault(package.package_type_id, []).append(package)

        units = []
        for package_type, type_packages in packages_by_type.items():
            commodities = []
            for package in type_packages:
                lines = self.move_line_ids.filtered(lambda l, package=package: l.result_package_id == package and l.quantity > 0)
                for line in lines:
                    product = line.product_id
                    nmfc = product.mycarrier_commodity_nmfc
                    if nmfc and not (nmfc.isdigit() and len(nmfc) == 4):
                        raise ValidationError(
                            f'Product "{product.name}" has an invalid MyCarrier NMFC "{nmfc}". '
                            'NMFC must be exactly 4 digits.')
                    if product.mycarrier_commodity_sub and not nmfc:
                        raise ValidationError(
                            f'Product "{product.name}" has a MyCarrier NMFC Sub but no NMFC. '
                            'NMFC is required whenever Sub is set.')
                    commodity = {
                        "commodityClass": product.mycarrier_commodity_class or "",
                        "commodityDescription": product.name,
                        "commodityHazMat": "",
                        "commodityNMFC": product.mycarrier_commodity_nmfc or "",
                        "commodityPackingType": "",
                        "commodityPieces": str(int(line.quantity)),
                        "commoditySub": product.mycarrier_commodity_sub or "",
                        "commodityWeight": str(int(line.quantity * product.weight)),
                        "customerOrderNumber": "",
                        "hazmatHazardClass": "",
                        "hazmatIDNumber": "",
                        "hazmatPackingGroup": "",
                        "hazmatProperShippingName": "",
                    }
                    if product in product_ids:
                        prod_mapping = mycarrier_instance.product_mapping_ids.filtered(lambda l, product=product: l.product_id == product)
                        commodity['productID'] = prod_mapping.mycarrier_product_id
                    commodities.append(commodity)
            if not commodities:
                continue
            units.append(
                {
                    "quoteCommodities": commodities,
                    "shippingUnitCount": str(len(type_packages)),
                    "shippingUnitType": package_type.name,
                    "unitHeight": str(int(package_type.height)),
                    "unitLength": str(int(package_type.packaging_length)),
                    "unitStackable": "No",
                    "unitWidth": str(int(package_type.width)),
                }
            )
        return units

    def _build_quote_units_package_wise(self):
        """Package-wise mode: one quoteUnit and one quoteCommodity per package - the whole
        pallet is one freight line, sourced from the package's own fields (weight, class,
        NMFC, NMFC Sub), never aggregated across same-type packages. Matches the client's
        Pallet_Package_MyCarrier_Guide.pdf reference (Commodity Description = package name,
        Pieces = 1, weight = package Shipping Weight)."""
        packages = self.move_line_ids.mapped('result_package_id')
        units = []
        for package in packages:
            self._validate_mycarrier_package(package)
            if not package.shipping_weight:
                raise ValidationError(f'Package {package.name} has no Shipping Weight set. Set it before sending to MyCarrier.')
            if not package.mycarrier_commodity_class:
                raise ValidationError(f'Package "{package.name}" has no MyCarrier Freight Class set. Set it before sending to MyCarrier.')
            nmfc = package.mycarrier_commodity_nmfc
            if not nmfc:
                raise ValidationError(f'Package "{package.name}" has no MyCarrier NMFC set. Set it before sending to MyCarrier.')
            if not (nmfc.isdigit() and len(nmfc) == 4):
                raise ValidationError(
                    f'Package "{package.name}" has an invalid MyCarrier NMFC "{nmfc}". '
                    'NMFC must be exactly 4 digits.')
            if not package.mycarrier_commodity_sub:
                raise ValidationError(f'Package "{package.name}" has no MyCarrier NMFC Sub set. Set it before sending to MyCarrier.')
            package_type = package.package_type_id
            commodity = {
                "commodityClass": package.mycarrier_commodity_class or "",
                "commodityDescription": package.name,
                "commodityHazMat": "",
                "commodityNMFC": nmfc or "",
                "commodityPackingType": "",
                "commodityPieces": str(package.mycarrier_package_count or 1),
                "commoditySub": package.mycarrier_commodity_sub or "",
                "commodityWeight": str(int(package.shipping_weight)),
                "customerOrderNumber": "",
                "hazmatHazardClass": "",
                "hazmatIDNumber": "",
                "hazmatPackingGroup": "",
                "hazmatProperShippingName": "",
            }
            units.append(
                {
                    "quoteCommodities": [commodity],
                    "shippingUnitCount": "1",
                    "shippingUnitType": package_type.name,
                    "unitHeight": str(int(package_type.height)),
                    "unitLength": str(int(package_type.packaging_length)),
                    "unitStackable": "No",
                    "unitWidth": str(int(package_type.width)),
                }
            )
        return units

    def validate_quote_info(self):
        for record in self:
            if record.destination_country_code != 'US':
                raise ValidationError(f'Destination country of {record.name} is not US')
            # if record.total_weight_done < 200:
            #     raise ValidationError(f'Total weight done of {record.name} is less than 200')
            if record.state in ('cancel', 'done'):
                raise ValidationError(f'{record.name} has been {record.state}')
        for record in self:
            record.create_mycarrier_quote_by_package()
