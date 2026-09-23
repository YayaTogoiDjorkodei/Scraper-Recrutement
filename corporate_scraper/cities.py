"""Morocco-first city lookup with a complete keyless API and offline cache."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import tempfile
from typing import Any

import requests


@dataclass(frozen=True, slots=True)
class City:
    name: str
    geoname_id: int | None = None
    region: str | None = None
    aliases: tuple[str, ...] = ()


class MoroccoCityService:
    """Fetch Moroccan cities without forcing a user to manage an API key.

    CountriesNow supplies the normal application's complete Morocco city list
    without an account. A configured GeoNames username still unlocks the
    legacy populated-place import when a company needs it.
    """

    COUNTRIES_NOW_URL = "https://countriesnow.space/api/v0.1/countries/cities"

    def __init__(self, cache_path: str | Path, session: requests.Session | None = None) -> None:
        self.cache_path = Path(cache_path)
        self.session = session or requests.Session()

    def load_cached(self) -> list[City]:
        try:
            content = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return []
        return [City(name=item["name"], geoname_id=item.get("geoname_id"), region=item.get("region"),
                     aliases=tuple(item.get("aliases", ()))) for item in content.get("cities", [])]

    def refresh(self, username: str = "", timeout: int = 15) -> list[City]:
        if username.strip():
            response = self.session.get(
                "https://api.geonames.org/searchJSON",
                params={"country": "MA", "featureClass": "P", "cities": "cities1000", "maxRows": 1000,
                        "orderby": "population", "lang": "fr", "username": username.strip()},
                timeout=timeout,
            )
            response.raise_for_status()
            cities = self._parse_geonames(response.json())
        else:
            response = self.session.post(self.COUNTRIES_NOW_URL, json={"country": "Morocco"}, timeout=timeout)
            response.raise_for_status()
            cities = self._parse_countries_now(response.json())
        self._write_cache(cities)
        return cities

    @staticmethod
    def manual(name: str) -> City:
        value = name.strip()
        if not value:
            raise ValueError("A manual city name cannot be empty.")
        return City(name=value)

    @staticmethod
    def _parse_geonames(payload: dict[str, Any]) -> list[City]:
        seen: set[int] = set()
        cities: list[City] = []
        for item in payload.get("geonames", []):
            name = str(item.get("name", "")).strip()
            identifier = item.get("geonameId")
            if not name or not isinstance(identifier, int) or identifier in seen:
                continue
            seen.add(identifier)
            aliases = tuple(dict.fromkeys(alias.strip() for alias in (item.get("toponymName"), item.get("asciiName"))
                                          if isinstance(alias, str) and alias.strip() and alias.casefold() != name.casefold()))
            cities.append(City(name=name, geoname_id=identifier, region=item.get("adminName1"), aliases=aliases))
        return cities

    @staticmethod
    def _parse_countries_now(payload: dict[str, Any]) -> list[City]:
        """Build a stable, deduplicated picker list from CountriesNow data."""
        cities: list[City] = []
        seen: set[str] = set()
        raw_cities = payload.get("data")
        if not isinstance(raw_cities, list):
            raise ValueError("The city API did not return a city list.")
        for raw_name in raw_cities:
            name = str(raw_name).strip()
            normalized = name.casefold()
            if not name or normalized in seen:
                continue
            seen.add(normalized)
            cities.append(City(name=name))
        if not cities:
            raise ValueError("The city API returned no Moroccan cities.")
        return sorted(cities, key=lambda city: city.name.casefold())

    def _write_cache(self, cities: list[City]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"country": "MA", "provider": "countriesnow.space", "cities": [asdict(city) for city in cities]}
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=self.cache_path.parent,
                                         prefix=f".{self.cache_path.name}.", suffix=".tmp") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            temporary_path = Path(handle.name)
        temporary_path.replace(self.cache_path)
