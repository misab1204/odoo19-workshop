{
    'name': "Animal Shelter",
    'depends': ['base'],
    'application': True,

    'data': [
        "security/ir.model.access.csv",
        "views/animals_views.xml",
        "views/animal_type_views.xml",
        "views/animal_location_views.xml",
        "views/animals_vaccine_views.xml",
        "views/animal_vaccination_views.xml",
        "views/animals_menus.xml"
    ],
}
