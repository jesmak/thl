"""Constants for the THL disease statistics integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "thl"

ATTRIBUTION: Final = "Data provided by Finnish Institute for Health and Welfare (THL)"

# THL's Sampo service. The dimensions file lists the diseases, weeks and areas; the data file holds the case numbers.
DIMENSIONS_URL: Final = "https://sampo.thl.fi/pivot/prod/{language}/ttr/casesweek/fact_ttr_casesweek.dimensions.json"
DATA_URL: Final = "https://sampo.thl.fi/pivot/prod/{language}/ttr/casesweek/fact_ttr_casesweek.json"
# Flu-like illness visits in primary care, from the same service.
ILI_DIMENSIONS_URL: Final = (
    "https://sampo.thl.fi/pivot/prod/{language}/infestat/infl/fact_infestat_infl.dimensions.json"
)
ILI_DATA_URL: Final = "https://sampo.thl.fi/pivot/prod/{language}/infestat/infl/fact_infestat_infl.json"
USER_AGENT: Final = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/106.0.5249.62 Safari/537.36"
)

# Languages of the disease and area names. THL's data is published in both.
LANGUAGES: Final = ["en", "fi"]

# The labels of the totals in THL's dimensions, which name the whole country and every week.
ALL_AREAS: Final = {"fi": "Kaikki hyvinvointialueet", "en": "All areas"}
ILI_ALL_AREAS: Final = {"fi": "Kaikki alueet", "en": "All areas"}
ALL_WEEKS: Final = {"fi": "Kaikki viikot", "en": "All times"}
WEEK_LABEL: Final = {"fi": "Vuosi {year} Viikko {week}", "en": "Year {year} Week {week}"}

# Config entry data. The keys are those of earlier versions, so existing entries keep working.
CONF_LANGUAGE: Final = "language"
CONF_DISEASE_ID: Final = "disease_id"
CONF_DISEASE_NAME: Final = "disease_name"
# Set once the past weeks have been written into the statistics of a subentry's sensors.
CONF_HISTORY_IMPORTED: Final = "history_imported"

# Each disease is a subentry of the one THL entry.
SUBENTRY_DISEASE: Final = "disease"
# Flu-like illness visits are a subentry of their own; there can be one.
SUBENTRY_ILI: Final = "ili"
ILI_UNIQUE_ID: Final = "thl_ili"
ILI_TITLE: Final = {"fi": "THL Influenssankaltaiset käynnit", "en": "THL Flu-like illness visits"}

# The measures of the case numbers cube, and of the flu-like illness cube.
MEASURE_CASES: Final = "877837"
MEASURE_INCIDENCE: Final = "931297"
MEASURE_ILI_VISITS: Final = "322060"
MEASURE_ALL_VISITS: Final = "323697"

# Sensor attributes.
ATTR_DISEASE_ID: Final = "disease_id"
ATTR_DISEASE_NAME: Final = "disease_name"
ATTR_LAST_WEEK: Final = "last_week"
ATTR_VALUES: Final = "values"

UPDATE_INTERVAL: Final = timedelta(minutes=30)
# The dimensions file is over 100 kB and changes once a week, so every sensor shares one copy of it.
DIMENSIONS_TTL: Final = timedelta(minutes=30)
# THL publishes a week's numbers with a lag, so the newest finished week is often still missing.
MAX_WEEK_FALLBACK: Final = 4
# How many weeks are written into the statistics of a new sensor, so its graphs have a past from the start.
HISTORY_WEEKS: Final = 26

# The areas of THL's data, and the ids they have in the sensor's attributes. Areas added later get an id
# made from their name.
AREA_IDS: Final[dict[int, str]] = {
    841988: "finland",
    837181: "ita-uudenmaan_hyvinvointialue",
    837147: "keski-uudenmaan_hyvinvointialue",
    839479: "lansi-uudenmaan_hyvinvointialue",
    838611: "vantaan_ja_keravan_hyvinvointialue",
    838879: "varsinais-suomen_hyvinvointialue",
    838312: "satakunnan_hyvinvointialue",
    840691: "kanta-hameen_hyvinvointialue",
    838364: "pirkanmaan_hyvinvointialue",
    836484: "paijat-hameen_hyvinvointialue",
    838636: "kymenlaakson_hyvinvointialue",
    837587: "etela-karjalan_hyvinvointialue",
    838539: "etela-savon_hyvinvointialue",
    841279: "pohjois-savon_hyvinvointialue",
    836414: "pohjois-karjalan_hyvinvointialue",
    836460: "keski-suomen_hyvinvointialue",
    841691: "etela-pohjanmaan_hyvinvointialue",
    836916: "pohjanmaan_hyvinvointialue",
    838714: "keski-pohjanmaan_hyvinvointialue",
    836191: "pohjois-pohjanmaan_hyvinvointialue",
    840852: "kainuun_hyvinvointialue",
    838893: "lapin_hyvinvointialue",
    839511: "helsingin_kaupunki",
    840333: "ahvenanmaa",
}

# The same areas in the flu-like illness cube, which numbers them differently.
ILI_AREA_IDS: Final[dict[int, str]] = {
    1200922: "finland",
    1200930: "ahvenanmaa",
    1200928: "etela-karjalan_hyvinvointialue",
    1200924: "etela-pohjanmaan_hyvinvointialue",
    1200917: "etela-savon_hyvinvointialue",
    1200925: "helsingin_kaupunki",
    1200944: "ita-uudenmaan_hyvinvointialue",
    1200929: "kainuun_hyvinvointialue",
    1200920: "kanta-hameen_hyvinvointialue",
    1200914: "keski-pohjanmaan_hyvinvointialue",
    1200933: "keski-suomen_hyvinvointialue",
    1200918: "keski-uudenmaan_hyvinvointialue",
    1200936: "kymenlaakson_hyvinvointialue",
    1200926: "lapin_hyvinvointialue",
    1200935: "lansi-uudenmaan_hyvinvointialue",
    1200934: "pirkanmaan_hyvinvointialue",
    1200932: "pohjanmaan_hyvinvointialue",
    1200919: "pohjois-karjalan_hyvinvointialue",
    1200923: "pohjois-pohjanmaan_hyvinvointialue",
    1200945: "pohjois-savon_hyvinvointialue",
    1200938: "paijat-hameen_hyvinvointialue",
    1200939: "satakunnan_hyvinvointialue",
    1200916: "vantaan_ja_keravan_hyvinvointialue",
    1200940: "varsinais-suomen_hyvinvointialue",
}

# Short names for the sensors of each area. THL's own names are long ("Etelä-Karjalan hyvinvointialue").
AREA_SHORT_NAMES: Final[dict[str, dict[str, str]]] = {
    "finland": {"fi": "Koko maa", "en": "Finland"},
    "ita-uudenmaan_hyvinvointialue": {"fi": "Itä-Uusimaa", "en": "East Uusimaa"},
    "keski-uudenmaan_hyvinvointialue": {"fi": "Keski-Uusimaa", "en": "Central Uusimaa"},
    "lansi-uudenmaan_hyvinvointialue": {"fi": "Länsi-Uusimaa", "en": "West Uusimaa"},
    "vantaan_ja_keravan_hyvinvointialue": {"fi": "Vantaa ja Kerava", "en": "Vantaa and Kerava"},
    "varsinais-suomen_hyvinvointialue": {"fi": "Varsinais-Suomi", "en": "Southwest Finland"},
    "satakunnan_hyvinvointialue": {"fi": "Satakunta", "en": "Satakunta"},
    "kanta-hameen_hyvinvointialue": {"fi": "Kanta-Häme", "en": "Kanta-Häme"},
    "pirkanmaan_hyvinvointialue": {"fi": "Pirkanmaa", "en": "Pirkanmaa"},
    "paijat-hameen_hyvinvointialue": {"fi": "Päijät-Häme", "en": "Päijät-Häme"},
    "kymenlaakson_hyvinvointialue": {"fi": "Kymenlaakso", "en": "Kymenlaakso"},
    "etela-karjalan_hyvinvointialue": {"fi": "Etelä-Karjala", "en": "South Karelia"},
    "etela-savon_hyvinvointialue": {"fi": "Etelä-Savo", "en": "South Savo"},
    "pohjois-savon_hyvinvointialue": {"fi": "Pohjois-Savo", "en": "North Savo"},
    "pohjois-karjalan_hyvinvointialue": {"fi": "Pohjois-Karjala", "en": "North Karelia"},
    "keski-suomen_hyvinvointialue": {"fi": "Keski-Suomi", "en": "Central Finland"},
    "etela-pohjanmaan_hyvinvointialue": {"fi": "Etelä-Pohjanmaa", "en": "South Ostrobothnia"},
    "pohjanmaan_hyvinvointialue": {"fi": "Pohjanmaa", "en": "Ostrobothnia"},
    "keski-pohjanmaan_hyvinvointialue": {"fi": "Keski-Pohjanmaa", "en": "Central Ostrobothnia"},
    "pohjois-pohjanmaan_hyvinvointialue": {"fi": "Pohjois-Pohjanmaa", "en": "North Ostrobothnia"},
    "kainuun_hyvinvointialue": {"fi": "Kainuu", "en": "Kainuu"},
    "lapin_hyvinvointialue": {"fi": "Lappi", "en": "Lapland"},
    "helsingin_kaupunki": {"fi": "Helsinki", "en": "Helsinki"},
    "ahvenanmaa": {"fi": "Ahvenanmaa", "en": "Åland"},
}
