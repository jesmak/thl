"""Constants for the THL disease statistics integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "thl"

ATTRIBUTION: Final = "Data provided by Finnish Institute for Health and Welfare (THL)"

# THL's Sampo service. The dimensions file lists the diseases, weeks and areas; the data file holds the case numbers.
DIMENSIONS_URL: Final = "https://sampo.thl.fi/pivot/prod/{language}/ttr/casesweek/fact_ttr_casesweek.dimensions.json"
DATA_URL: Final = "https://sampo.thl.fi/pivot/prod/{language}/ttr/casesweek/fact_ttr_casesweek.json"
USER_AGENT: Final = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/106.0.5249.62 Safari/537.36"
)

# Languages of the disease and area names. THL's data is published in both.
LANGUAGES: Final = ["en", "fi"]

# The labels of the totals in THL's dimensions, which name the whole country and every week.
ALL_AREAS: Final = {"fi": "Kaikki hyvinvointialueet", "en": "All areas"}
ALL_WEEKS: Final = {"fi": "Kaikki viikot", "en": "All times"}
WEEK_LABEL: Final = {"fi": "Vuosi {year} Viikko {week}", "en": "Year {year} Week {week}"}

# Config entry data. The keys are those of earlier versions, so existing entries keep working.
CONF_LANGUAGE: Final = "language"
CONF_DISEASE_ID: Final = "disease_id"
CONF_DISEASE_NAME: Final = "disease_name"

# Each disease is a subentry of the one THL entry.
SUBENTRY_DISEASE: Final = "disease"

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
