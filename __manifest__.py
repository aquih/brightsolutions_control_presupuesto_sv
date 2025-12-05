{
    'name': 'brightsolutions_control_presupuesto',
    'version': '1.0.6',
    'description': 'brightsolutions_control_presupuesto',
    'summary': 'Control del presupuesto para ordenes de compra',
    'license': 'LGPL-3',
    'depends': [
        'base', 'sale', 'purchase', 'bright_solutions_sv'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/purchase_order_view.xml',
        'views/purchase_order_line_view.xml',
        'wizards/auth_popup_wz_view.xml',
        'views/menues.xml',
    ],
    'auto_install': True,
    'application': False,
}
