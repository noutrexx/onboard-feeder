from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from models import FeedItemCreate


@dataclass(frozen=True)
class CityLocation:
    city: str
    lat: float
    lng: float
    aliases: tuple[str, ...] = ()


TURKEY_CITIES: tuple[CityLocation, ...] = (
    CityLocation("Adana", 37.0000, 35.3213),
    CityLocation("Adıyaman", 37.7648, 38.2786, ("Adiyaman",)),
    CityLocation("Afyonkarahisar", 38.7507, 30.5567, ("Afyon",)),
    CityLocation("Ağrı", 39.7191, 43.0503, ("Agri",)),
    CityLocation("Aksaray", 38.3687, 34.0370),
    CityLocation("Amasya", 40.6499, 35.8353),
    CityLocation("Ankara", 39.9334, 32.8597),
    CityLocation("Antalya", 36.8969, 30.7133),
    CityLocation("Ardahan", 41.1105, 42.7022),
    CityLocation("Artvin", 41.1828, 41.8183),
    CityLocation("Aydın", 37.8560, 27.8416, ("Aydin",)),
    CityLocation("Balıkesir", 39.6484, 27.8826, ("Balikesir",)),
    CityLocation("Bartın", 41.6358, 32.3375, ("Bartin",)),
    CityLocation("Batman", 37.8812, 41.1351),
    CityLocation("Bayburt", 40.2552, 40.2249),
    CityLocation("Bilecik", 40.1426, 29.9793),
    CityLocation("Bingöl", 38.8847, 40.4939, ("Bingol",)),
    CityLocation("Bitlis", 38.4006, 42.1095),
    CityLocation("Bolu", 40.7395, 31.6116),
    CityLocation("Burdur", 37.7203, 30.2908),
    CityLocation("Bursa", 40.1826, 29.0665),
    CityLocation("Çanakkale", 40.1553, 26.4142, ("Canakkale",)),
    CityLocation("Çankırı", 40.6013, 33.6134, ("Cankiri",)),
    CityLocation("Çorum", 40.5506, 34.9556, ("Corum",)),
    CityLocation("Denizli", 37.7765, 29.0864),
    CityLocation("Diyarbakır", 37.9144, 40.2306, ("Diyarbakir",)),
    CityLocation("Düzce", 40.8438, 31.1565, ("Duzce",)),
    CityLocation("Edirne", 41.6771, 26.5557),
    CityLocation("Elazığ", 38.6743, 39.2232, ("Elazig",)),
    CityLocation("Erzincan", 39.7500, 39.5000),
    CityLocation("Erzurum", 39.9000, 41.2700),
    CityLocation("Eskişehir", 39.7767, 30.5206, ("Eskisehir",)),
    CityLocation("Gaziantep", 37.0662, 37.3833, ("Antep",)),
    CityLocation("Giresun", 40.9128, 38.3895),
    CityLocation("Gümüşhane", 40.4386, 39.5086, ("Gumushane",)),
    CityLocation("Hakkari", 37.5833, 43.7333),
    CityLocation("Hatay", 36.4018, 36.3498, ("Antakya",)),
    CityLocation("Iğdır", 39.9167, 44.0333, ("Igdir",)),
    CityLocation("Isparta", 37.7648, 30.5566),
    CityLocation("İstanbul", 41.0082, 28.9784, ("Istanbul",)),
    CityLocation("İzmir", 38.4237, 27.1428, ("Izmir",)),
    CityLocation("Kahramanmaraş", 37.5753, 36.9228, ("Kahramanmaras", "Maras", "Maraş")),
    CityLocation("Karabük", 41.2061, 32.6204, ("Karabuk",)),
    CityLocation("Karaman", 37.1759, 33.2287),
    CityLocation("Kars", 40.6013, 43.0975),
    CityLocation("Kastamonu", 41.3887, 33.7827),
    CityLocation("Kayseri", 38.7205, 35.4826),
    CityLocation("Kilis", 36.7184, 37.1212),
    CityLocation("Kırıkkale", 39.8468, 33.5153, ("Kirikkale",)),
    CityLocation("Kırklareli", 41.7351, 27.2252, ("Kirklareli",)),
    CityLocation("Kırşehir", 39.1425, 34.1709, ("Kirsehir",)),
    CityLocation("Kocaeli", 40.8533, 29.8815, ("Izmit", "İzmit")),
    CityLocation("Konya", 37.8746, 32.4932),
    CityLocation("Kütahya", 39.4167, 29.9833, ("Kutahya",)),
    CityLocation("Malatya", 38.3552, 38.3095),
    CityLocation("Manisa", 38.6191, 27.4289),
    CityLocation("Mardin", 37.3212, 40.7245),
    CityLocation("Mersin", 36.8121, 34.6415),
    CityLocation("Muğla", 37.2153, 28.3636, ("Mugla",)),
    CityLocation("Muş", 38.9462, 41.7539, ("Mus",)),
    CityLocation("Nevşehir", 38.6244, 34.7239, ("Nevsehir",)),
    CityLocation("Niğde", 37.9667, 34.6833, ("Nigde",)),
    CityLocation("Ordu", 40.9862, 37.8797),
    CityLocation("Osmaniye", 37.0742, 36.2478),
    CityLocation("Rize", 41.0201, 40.5234),
    CityLocation("Sakarya", 40.7569, 30.3781, ("Adapazari", "Adapazarı")),
    CityLocation("Samsun", 41.2928, 36.3313),
    CityLocation("Şanlıurfa", 37.1674, 38.7955, ("Sanliurfa", "Urfa")),
    CityLocation("Siirt", 37.9333, 41.9500),
    CityLocation("Sinop", 42.0231, 35.1531),
    CityLocation("Şırnak", 37.4187, 42.4918, ("Sirnak",)),
    CityLocation("Sivas", 39.7477, 37.0179),
    CityLocation("Tekirdağ", 40.9780, 27.5110, ("Tekirdag",)),
    CityLocation("Tokat", 40.3167, 36.5500),
    CityLocation("Trabzon", 41.0015, 39.7178),
    CityLocation("Tunceli", 39.3074, 39.4388),
    CityLocation("Uşak", 38.6823, 29.4082, ("Usak",)),
    CityLocation("Van", 38.5012, 43.3729),
    CityLocation("Yalova", 40.6500, 29.2667),
    CityLocation("Yozgat", 39.8181, 34.8147),
    CityLocation("Zonguldak", 41.4564, 31.7987),
)


def normalize_text(value: str) -> str:
    lowered = value.casefold()
    without_marks = "".join(
        character
        for character in unicodedata.normalize("NFKD", lowered)
        if not unicodedata.combining(character)
    )
    return without_marks.translate(str.maketrans({"ı": "i", "İ": "i"}))


def extract_location(text: str) -> dict[str, object]:
    normalized_text = normalize_text(text)

    for city in TURKEY_CITIES:
        candidates = (city.city, *city.aliases)
        for candidate in candidates:
            normalized_candidate = normalize_text(candidate)
            pattern = rf"(?<![a-z0-9])#?{re.escape(normalized_candidate)}(?![a-z0-9])"
            if re.search(pattern, normalized_text):
                return {
                    "has_location": True,
                    "location_tag": f"konum:{city.city}",
                    "location_city": city.city,
                    "location_text": candidate,
                    "location_lat": city.lat,
                    "location_lng": city.lng,
                    "location_confidence": 0.92 if candidate == city.city else 0.84,
                }

    return {
        "has_location": False,
        "location_tag": None,
        "location_city": None,
        "location_text": None,
        "location_lat": None,
        "location_lng": None,
        "location_confidence": None,
    }


def enrich_item_location(item: FeedItemCreate) -> FeedItemCreate:
    location = extract_location(f"{item.title} {item.description}")
    return item.model_copy(update=location)


def enrich_items_location(items: list[FeedItemCreate]) -> list[FeedItemCreate]:
    return [enrich_item_location(item) for item in items]
