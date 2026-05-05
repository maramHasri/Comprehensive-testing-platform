from flask_restx import Namespace, Resource, fields

from app.models import Country, Region


countries_ns = Namespace(
    "Countries",
    description="Lightweight geographic data for registration and institution profile location.",
)

country_model = countries_ns.model(
    "Country",
    {
        "id": fields.Integer(required=True),
        "code": fields.String(required=True, description="ISO-like country code"),
        "name": fields.String(required=True),
    },
)

region_model = countries_ns.model(
    "Region",
    {
        "id": fields.Integer(required=True),
        "country_id": fields.Integer(required=True),
        "code": fields.String(required=False),
        "name": fields.String(required=True),
    },
)

countries_response_model = countries_ns.model(
    "CountriesResponse",
    {
        "countries": fields.List(fields.Nested(country_model), required=True),
    },
)

regions_response_model = countries_ns.model(
    "RegionsResponse",
    {
        "country_id": fields.Integer(required=True),
        "regions": fields.List(fields.Nested(region_model), required=True),
    },
)


@countries_ns.route("/countries")
class CountryList(Resource):
    @countries_ns.doc(
        "list_countries",
        description="Return all countries for registration/onboarding dropdown.",
    )
    @countries_ns.response(200, "OK", countries_response_model)
    def get(self):
        rows = Country.query.order_by(Country.name.asc()).all()
        countries = [{"id": c.id, "code": c.code, "name": c.name} for c in rows]
        return {"countries": countries}, 200


@countries_ns.route("/countries/<int:country_id>/regions")
class CountryRegions(Resource):
    @countries_ns.doc(
        "list_country_regions",
        description=(
            "Return optional administrative divisions for a selected country. "
            "If none exist, returns an empty array."
        ),
    )
    @countries_ns.response(200, "OK", regions_response_model)
    @countries_ns.response(404, "Country not found")
    def get(self, country_id: int):
        country = Country.query.get(country_id)
        if country is None:
            return {"message": "Country not found."}, 404
        rows = Region.query.filter_by(country_id=country_id).order_by(Region.name.asc()).all()
        regions = [{"id": r.id, "country_id": r.country_id, "code": r.code, "name": r.name} for r in rows]
        return {"country_id": country_id, "regions": regions}, 200
