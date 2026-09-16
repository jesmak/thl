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

A custom component that follows the weekly case numbers of infectious diseases from the open data of the Finnish
Institute for Health and Welfare (THL). Each disease is added separately, and gets a sensor with last week's cases in
the whole country and in every wellbeing services county.

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
out of the list.

To change the language later, choose **Reconfigure** from the integration's menu. Every disease being followed is
renamed in the new language, and so are the areas in the sensor attributes. The ids in the attributes never change.

| Name     | Type | Description                                              | Default                   |
| -------- | ---- | -------------------------------------------------------- | ------------------------- |
| Language | enum | The language of the disease and area names: `fi` or `en` | Home Assistant's language |
| Disease  | enum | One of the diseases THL reports weekly                   |                           |

## Sensor

The state is last week's number of cases in the whole country. The sensor is named after the disease, for example
`sensor.thl_influenssa`.

| Attribute                    | Description                       |
| ---------------------------- | --------------------------------- |
| `last_week`                  | The week the numbers are from     |
| `values`                     | Each area with its numbers, below |
| `disease_id`, `disease_name` | The disease in THL's data         |
| `attribution`                | Data credit                       |

Each area in `values` has:

| Key                    | Description                                    |
| ---------------------- | ---------------------------------------------- |
| `name`                 | The area's name in the chosen language         |
| `area_id`              | The area's id, `finland` for the whole country |
| `amount_last_week`     | Cases last week                                |
| `amount_two_weeks_ago` | Cases the week before                          |
| `change_in_numbers`    | The difference between the two weeks           |
| `change_percentage`    | The difference as a percentage                 |

The three change figures are missing when THL hasn't published the week before. THL publishes a week's numbers with a
lag, so the sensor uses the newest week that has been published, up to four weeks back. The areas aren't stored in the
recorder, only the state. The sensor is unavailable while THL can't be reached.

## Upgrading from 1.x

Nothing needs to be done. Versions before 2.0 made a separate integration entry for each disease; on the first start
they are merged into one entry with a disease inside it for each. Entity IDs and unique IDs stay as they were, so
history, statistics, dashboards, automations and thl-card keep working. The language of the merged entry is the one
most of the old entries used.

## Data

Disease statistics: [THL](https://thl.fi/), from the open data of the infectious diseases register.

## Development

Requires Python 3.14.

```
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
.venv/bin/ruff check .
```

| Path                           | What it contains                                     |
| ------------------------------ | ---------------------------------------------------- |
| `__init__.py`                  | Setup, and the shared dimensions                     |
| `migration.py`                 | Merging the entries of 1.x into one                  |
| `config_flow.py`               | The language, and a subentry per disease             |
| `api.py`                       | THL's service, and one shared copy of the dimensions |
| `statistics.py`                | Reading the dimensions and the case numbers          |
| `coordinator.py`               | Fetching the newest published week every half hour   |
| `sensor.py`                    | The sensor                                           |
| `translations/<language>.json` | Home Assistant UI texts                              |

[commits-shield]: https://img.shields.io/github/commit-activity/y/jesmak/thl.svg?style=for-the-badge
[commits]: https://github.com/jesmak/thl/commits/main
[license-shield]: https://img.shields.io/github/license/jesmak/thl.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/jesmak/thl.svg?style=for-the-badge
[releases]: https://github.com/jesmak/thl/releases
