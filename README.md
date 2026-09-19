# THL disease statistics for Home Assistant

Home Assistant integration for the weekly infectious disease numbers published by the Finnish Institute for Health and
Welfare (THL).

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![GitHub Activity][commits-shield]][commits]

## Support

Hey dude! Help me out for a couple of :beers: or a :coffee:!

[![coffee](https://www.buymeacoffee.com/assets/img/custom_images/black_img.png)](https://www.buymeacoffee.com/jesmak)

## What is it?

A custom component that follows the weekly numbers of infectious diseases from the open data of the Finnish Institute
for Health and Welfare (THL). Each disease is added separately, and gets sensors for its cases and its incidence per
100 000 people, in the whole country and in every wellbeing services county.

It can also follow **flu-like illness visits** in primary care: the share of all visits made for influenza-like
illness, in the whole country and in every county. These show a flu season starting before the lab-confirmed cases do.

New sensors get the past six months written into their statistics, so graphs have a history from the start.

The numbers can be shown with [thl-card](https://github.com/jesmak/thl-card), which draws them on a map of Finland.

## Installation

### With HACS

1. Add this repository to HACS custom repositories with type **Integration**
2. Search for THL disease statistics in HACS and download it
3. Restart Home Assistant
4. Add the integration in Settings › Devices & services, and choose a disease

### Manual

1. Download the source code from the latest release
2. Copy the `custom_components/thl` folder to your Home Assistant installation's `config/custom_components` folder
3. Restart Home Assistant
4. Add the integration in Settings › Devices & services, and choose a disease

## Settings

Adding the integration takes two steps: first the language, then the first disease from the list THL reports. Every
further disease is added from the integration page with **Add disease**; the diseases already being followed are left
out of the list. The flu-like illness visits are added from the same page with **Add flu-like illness visits**.

To change the language later, choose **Reconfigure** from the integration's menu. Everything being followed is
renamed in the new language, and so are the areas in the sensor attributes. The ids in the attributes never change.

| Name     | Type | Description                                              | Default                   |
| -------- | ---- | -------------------------------------------------------- | ------------------------- |
| Language | enum | The language of the disease and area names: `fi` or `en` | Home Assistant's language |
| Disease  | enum | One of the diseases THL reports weekly                   |                           |

## Sensors

THL publishes a week's numbers during the following week, so every sensor shows the newest week that has been
published, up to four weeks back. Its `last_week` attribute tells which week that is. A sensor is unavailable while
THL can't be reached.

### A disease

Each disease is a device named after it, such as **THL Influenssa**, with these sensors:

| Sensor                                       | State                                  | Example                                            |
| -------------------------------------------- | -------------------------------------- | -------------------------------------------------- |
| The disease                                  | Cases in the whole country             | `sensor.thl_influenssa`                            |
| Incidence                                    | Cases per 100 000 in the whole country | `sensor.thl_influenssa_ilmaantuvuus`               |
| One per wellbeing services county            | Cases in the county                    | `sensor.thl_influenssa_etela_karjala`              |
| One per wellbeing services county, incidence | Cases per 100 000 in the county        | `sensor.thl_influenssa_etela_karjala_ilmaantuvuus` |

Incidence is what makes the counties comparable: a large county has more cases simply because more people live there.

The whole country's cases sensor carries every area in its `values` attribute, which is what thl-card reads:

| Key                       | Description                                    |
| ------------------------- | ---------------------------------------------- |
| `name`                    | The area's name in the chosen language         |
| `area_id`                 | The area's id, `finland` for the whole country |
| `amount_last_week`        | Cases last week                                |
| `amount_two_weeks_ago`    | Cases the week before                          |
| `change_in_numbers`       | The difference between the two weeks           |
| `change_percentage`       | The difference as a percentage                 |
| `incidence_last_week`     | Cases per 100 000 last week                    |
| `incidence_two_weeks_ago` | Cases per 100 000 the week before              |
| `entity_id`               | The area's cases sensor                        |
| `incidence_entity_id`     | The area's incidence sensor                    |

The figures of the week before are missing when THL hasn't published it. The `values` attribute isn't stored in the
recorder; each area's own sensors are.

### Flu-like illness visits

A device named **THL Influenssankaltaiset käynnit** (or **THL Flu-like illness visits**), with a sensor for the
whole country and one per county. The state is the percentage of all primary care visits that were made for
influenza-like illness. It is a small number outside the flu season: around 0.01 %.

The whole country's sensor carries every area in its `values` attribute:

| Key                    | Description                                       |
| ---------------------- | ------------------------------------------------- |
| `name`, `area_id`      | As for a disease                                  |
| `share_last_week`      | The share of flu-like illness visits last week, % |
| `share_two_weeks_ago`  | The same the week before                          |
| `visits_last_week`     | Visits for flu-like illness last week             |
| `all_visits_last_week` | All primary care visits last week                 |
| `entity_id`            | The area's sensor                                 |

## The history

When a sensor is added, the past six months are written into its statistics. Each week's figure is placed at the start
of the week after it, which is when the sensor would have shown it, so the past and what the recorder keeps from then
on line up. A sensor that already has statistics of its own keeps them untouched.

A graph therefore shows each week about a week after the week it describes. The shape of the curve is the same.

## Usage with apexcharts-card

[apexcharts-card](https://github.com/RomRider/apexcharts-card) can draw a county's incidence from its statistics:

```yaml
type: custom:apexcharts-card
graph_span: 26w
header:
  show: true
  title: Influenssa, Etelä-Karjala
  show_states: true
series:
  - entity: sensor.thl_influenssa_etela_karjala_ilmaantuvuus
    statistics:
      type: mean
      period: day
    curve: stepline
  - entity: sensor.thl_influenssa_ilmaantuvuus
    name: Koko maa
    statistics:
      type: mean
      period: day
    curve: stepline
```

## Upgrading from 1.x

Nothing needs to be done. Versions before 2.0 made a separate integration entry for each disease; on the first start
they are merged into one entry with a disease inside it for each. Entity IDs and unique IDs stay as they were, so
history, statistics, dashboards, automations and thl-card keep working. The language of the merged entry is the one
most of the old entries used.

The county, incidence and flu-like illness sensors are new, and appear with six months of history. The disease sensors
that already existed keep the history they have.

## Data

Disease statistics and primary care visits: [THL](https://thl.fi/), from the open data of the infectious diseases
register and the primary health care register (Avohilmo).

## Development

Requires Python 3.14.

```
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
.venv/bin/ruff check .
```

| Path                           | What it contains                                                              |
| ------------------------------ | ----------------------------------------------------------------------------- |
| `__init__.py`                  | Setup, and the shared dimensions                                              |
| `migration.py`                 | Merging the entries of 1.x into one                                           |
| `config_flow.py`               | The language, a subentry per disease, and one for the flu-like illness visits |
| `api.py`                       | THL's service, and one shared copy of each dimensions file                    |
| `statistics.py`                | Reading the dimensions and data files                                         |
| `coordinator.py`               | Fetching the newest published weeks every half hour                           |
| `sensor.py`                    | The sensors                                                                   |
| `history.py`                   | Writing past weeks into the statistics of new sensors                         |
| `translations/<language>.json` | Home Assistant UI texts                                                       |

[commits-shield]: https://img.shields.io/github/commit-activity/y/jesmak/thl.svg?style=for-the-badge
[commits]: https://github.com/jesmak/thl/commits/main
[license-shield]: https://img.shields.io/github/license/jesmak/thl.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/jesmak/thl.svg?style=for-the-badge
[releases]: https://github.com/jesmak/thl/releases
