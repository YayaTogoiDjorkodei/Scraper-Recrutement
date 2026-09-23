from corporate_scraper.cities import MoroccoCityService


class Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {"geonames": [
            {"geonameId": 2553604, "name": "Casablanca", "asciiName": "Casablanca", "adminName1": "Casablanca-Settat"},
            {"geonameId": 2538475, "name": "Fès", "asciiName": "Fes", "toponymName": "Fes", "adminName1": "Fès-Meknès"},
        ]}


class Session:
    def __init__(self): self.calls = []
    def get(self, url, params, timeout):
        self.calls.append((url, params, timeout))
        return Response()


class CountriesNowResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"data": ["Casablanca", "Rabat", "Casablanca", "Agadir"]}


class CountriesNowSession(Session):
    def post(self, url, json, timeout):
        self.calls.append((url, json, timeout))
        return CountriesNowResponse()


def test_refresh_is_morocco_only_and_cache_is_reusable(tmp_path):
    session = Session()
    service = MoroccoCityService(tmp_path / "cities.json", session)

    cities = service.refresh("account")

    assert session.calls[0][1]["country"] == "MA"
    assert session.calls[0][1]["lang"] == "fr"
    assert [(city.name, city.aliases) for city in cities] == [("Casablanca", ()), ("Fès", ("Fes",))]
    assert MoroccoCityService(tmp_path / "cities.json").load_cached() == cities


def test_keyless_refresh_populates_complete_moroccan_cities_without_a_username(tmp_path):
    session = CountriesNowSession()
    service = MoroccoCityService(tmp_path / "cities.json", session)
    cities = service.refresh()

    assert session.calls[0][0] == MoroccoCityService.COUNTRIES_NOW_URL
    assert session.calls[0][1] == {"country": "Morocco"}
    assert [city.name for city in cities] == ["Agadir", "Casablanca", "Rabat"]


def test_manual_city_is_available_when_needed(tmp_path):
    service = MoroccoCityService(tmp_path / "cities.json", Session())
    assert service.manual("  Kénitra ").name == "Kénitra"
