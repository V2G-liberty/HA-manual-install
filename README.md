# DEPRECATED
This repository is no longer supported.  It has been replaced by [HA add-on V2G Liberty](https://github.com/V2G-liberty/addon-v2g-liberty). 


## V2G Liberty manual install

This integration lets you add full automatic and price optimized control over Vehicle to grid (V2G) charging. It has a 
practical local app in [HomeAssistant](https://www.home-assistant.io/) and uses the smart EMS [FlexMeasures](https://flexmeasures.io) for optimized schedules.

The schedules are optimized on day-ahead energy prices, so this works best with an electricity contract with dynamic (hourly) prices[^1].
We intend to add optimisation for your solar generation in the near future.

[^1]: For now: most Dutch energy suppliers are listed and all European energy prices (EPEX) are available for optimisation. There also is an option to upload your own prices, if you have an interest in this, please [contact us](https://v2g-liberty.eu/) to see what the options are.

For none European markets (e.g. Australia) there is an option to work with own-prices that can be uploaded to FlexMeasures (we are working on an extension of V2G Liberty so this can be handled within Home Assistant.)

You can read more about the project and its vision [here](https://v2g-liberty.eu/) and [here](https://seita.nl/project/v2ghome-living-lab/).

In practice, V2G Liberty does the following:
- In automatic mode:
  - No worries, just plugin when you return home and let the system automatically optimize charging. 
  - Make car reservations (e.g. be charged 100% at 7am tomorrow) through your own calendar (eg. gGoogle or iCloud)
- Override the system and set charging to "Max Boost Now" mode in cases where you need as much battery SoC a possible quickly.

This integration is a Python app and uses:

- FlexMeasures for optimizing charging schedules. FlexMeasures is periodically asked to generate optimized charging schedules.
- Home Assistant for automating local control over your Wallbox Quasar. V2G Liberty translates this into set points which it sends to the Wallbox Quasar via modbus.
- The AppDaemon addon for Home Assistant for running the Python app.

![V2G Liberty Architecture](https://user-images.githubusercontent.com/6270792/216368533-aa07dfa7-6e20-47cb-8778-aa2b8ba8b6e1.png)

### Prerequisites
 
At the time of writing, 2024-03, only the [Wallbox Quasar 1 charger](https://wallbox.com/en_uk/quasar-dc-charger) is supported.
This is a [CHAdeMO](https://www.chademo.com/) compatible charger.
Compatible cars that can do V2G with this protocol are the [Nissan Leaf](https://ev-database.org/car/1657/Nissan-Leaf-eplus) (also earlier models) and [Nissan Evalia](https://ev-database.org/car/1117/Nissan-e-NV200-Evalia).
When the Wallbox Quasar 2 is available we expect V2G Liberty to be compatible with this hardware "out of the box".
Then also CCS V2G capable cars can be managed with V2G Liberty.
Hopefully other chargers will follow soon.

## Preparation

Before installing or activation of V2G Liberty, please make sure that charging and discharging with the car and charger works properly.
Test this with the app supplied with the charger.
This is important because V2G Liberty will 'take control' over the charger.
Operating the charger either through the screen of the charger or the app will not work (reliably) any more when V2G Liberty is active.

### FlexMeasures

The cloud backend [FlexMeasures](https://github.com/FlexMeasures/flexmeasures) provides the smart schedules needed for optimizing the charging and discharging.
You can run your own instance of FlexMeasures, but you can also make use of an instance run by Seita.
If you prefer this option, please [contact us](https://v2g-liberty.eu).

### Home assistant

As said, Home Assistant (from now on we’ll abbreviate this to HA) forms the basis of V2G Liberty.
So before you can start with V2G Liberty you'll need a running HA in your network. Both HA and the charger need to be on the same network and must be able to communicate.
HA typically runs on a small computer, e.g. a Raspberry PI, but it can also run on a NAS or an old laptop.
HA has some [suggestions for hardware](https://www.home-assistant.io/blog/2022/04/16/device-to-run-home-assistant/).
For the installation of HA on your (edge) computer, [guides](https://www.home-assistant.io/getting-started/) can be found online and help can be sought in many active forums.

### An electricity contract with dynamic prices

As said, the software optimizes for EPEX day-ahead prices, so a contract of this type is the best option.
There is no rush, though.
You can try out V2G Liberty first and later on get the dynamic contract.
In the Netherlands there are several suppliers, o.a. ANWB, Energy Zero, Tibber, Zonneplan, etc.
This changes the way your electricity is priced and billed, so it is wise to find information and make sure you really understand what this means for your situation before making this change.

### Get a GitHub account

You’ll need a GitHub account for getting the V2G Liberty source code and for setting up HACS (see later).
So go ahead and [get a GitHub account](https://github.com/signup) (it is free) if you do not have this yet.

### Get an online calendar

For the situations where you would like the car to be fully charged, e.g. for a longer trip, V2G Liberty optimizes on a dedicated digital (online) calendar.
An online/digital calendar is mandatory, without it V2G Liberty cannot work.

It is of course most useful if the calendar is integrated with your normal calendar and if you can easily edit the calendar items on your smartphone (outside HA / V2G Liberty).
You make the appointments on your phone or laptop directly, not through HA.
Home Assistant only reads the appointments from the online calendar.
Options are, for example:
- A CalDav compatible calendar. E.g. NextCloud or OwnCloud if you’d like an open-source solution
- iCloud, this can be reached through CalDav (or through the HA integration – no examples yet)
- Google calendar<br>
This from early 2024 can also be reached via CalDav but has not been tested yet with V2G Liberty (if you've got experience with this, please let us know!). See: https://developers.google.com/calendar/caldav/v2/guide.<br>
The Google calendar is confirmed to work with the HA Google Calendar integration in Home Assistant (not to be confused with Google Assistant).

- Office 365. Via non-official O365-HomeAssistant integration, see GitHub
- ICS Calendar (or iCalendar) integration, also non-official. It can be found on HACS.

We recommend a separate calendar for your car reservations.
Filtering only the car reservations is also an option.
The result must be that in Home Assistant only the events meant for the car are present.
Preferably name the calendar (`car_reservation`). If you name(d) it otherwise, update the calendar name in the configuration of V2G Liberty secrets.yaml and in the v2g_liberty_dashboard.yaml

---

## Installation

Now that you have a running Home Assistant, you're ready to install V2G Liberty in Home Assistant.
We'll take you through the process step by step.

### Install the AppDaemon 4 add-on

AppDaemon is an official add-on for HA and thus can be installed from within HA.

Please go to `Settings -> Add-ons -> Add-on store` and find and install the AppDaemon add-on.

***After the update > 0.14 the folder structure and location has changed., please take extra attention to setting folders and files in the right place.***

When installed AppDaemon needs to be configured, look for (`Settings -> Addons -> AppDaemon 4 -> Configuration`), add the following Python packages and click `save`:

```yaml
python_packages:
  - isodate
  - pyModbus
```

### Install HACS

The Home Assistant Community Store (HACS) has loads of integrations that are not in the official store of HA.
You'll need two of these and that's why you also need to install this add-on.
It is explained on the [HACS installation pages](https://hacs.xyz).
As a reference you might find this [instruction video](https://www.youtube.com/watch?v=D6ZlhE-Iv9E) a handy resource.

#### Add modules to HA via HACS

Add the following modules to HA through HACS:
- [ApexChart-card](https://github.com/RomRider/apexcharts-card)<br>
  This is needed for graphs in the user interface.
- [Custom-card](https://github.com/thomasloven/lovelace-card-mod)<br>
  This is needed for a better UI.

There are other modules that might look interesting, like Leaf Spy, but you do not need any of these for V2G-L.
After installation the reference to these resources has to be added through menu:
1. Make sure, advanced mode is enabled in your user profile (click on your username to get there)
2. Navigate to Settings -> Dashboards -> from the top right menu (&vellip;) select resources.
3. Click (+ ADD RESOURCE) button and enter URL `/hacsfiles/apexcharts-card/apexcharts-card.js` and select type "JavaScript Module".
4. Repeat for `/hacsfiles/lovelace-card-mod/card-mod.js`
5. Restart Home Assistant.

### Install Samba share Add-on (optional)

This lets you handle files in HA from a remote computer. This makes copying and editing much easier, so it is highly recommended to install and use this add-on. This is also an official add-on for HA and thus can be installed from within HA.

Again go to `Settings -> Add-ons -> Add-on store` and find and install the Samba share add-on.

When installed the add-on needs to be configured, look for (`Settings -> Addons -> Samba share -> Configuration`). Create a username and set a password (leave workgroup to WORKGROUP) and click `save`.

In the documentation tab you'll find instructions on how to connect your computer to the Samba share. You'll have to connect to the `addon_configs` share and to the `config` share.

If this does not work for you the files can also be copied and edited via the add-on "File editor". This is not explained in further detail here.

## Configure HA

### Copy & edit files

If you've not already done so, download the newest [V2G Liberty files](https://github.com/V2G-liberty/HA-manual-install/archive/refs/heads/main.zip) from GitHub to your computer and un-pack/un-zip. You'll have two folders that need to be copied to their respective locations.

Copy these files (via Samba share) so that the following folders and files are created:

```
. (root = Addon config folder)
a0d7b954_appdaemon
├── appdaemon.yaml ①
├── apps
│   ├── apps.yaml ①
│   └── v2g-liberty
│       ├── constants.py
│       ├── flexmeasures_client.py
│       ├── get_fm_data.py
│       ├── LICENSE
│       ├── modbus_evse_client.py
│       ├── README.md
│       ├── set_fm_data.py
│       ├── v2g_globals.py
│       └── v2g_liberty.py
│    
└── logs ②
    ├── appdaemon_error.log
    └── appdaemon_main.log 
```
① If you had AppDaemon already configured and/or have other apps you'll have to add the contents of the downloaded files to your current files instead of overwriting them.

② This folfer is not in the downloaded zip-file. Check if this folder exists, if not create it manually. The .log files in it will be automatically created by AppDaemon once it runs.


```
. (root = HA config folder)
├── packages
│   └── v2g_liberty
│       ├── table_style.yaml
│       ├── v2g-liberty-dashboard.yaml
│       ├── v2g-liberty-package.yaml
│       └── v2g_liberty_ui_module_stats.yaml
├── configuration.yaml ③
└── secrets.yaml ③
```

③ These files need to be edited by you, see next steps.

### Create configuration

This is not complicated, but you'll need to work precise. The configuration of HA is stored in .yaml files, these can be edited in the HA file editor (in the left main menu).

  > If you have installed V2G Liberty before, please remove any changes made during that installation to the .yaml files.

After completion of this step you'll end up with a these files and folders (others might be there but are not shown here). Some might be already present and only need editing. Others files or folders might need to added. The files you'll have to edit are marked with *.

### Secrets

HA stores secrets in the file `secrets.yaml`. V2G Liberty stores both secrets and configuration values in this file. It can be found in the root of the `config` folder (share).

Open this file with a text editor on your computer (or in the HA file editor if you like) and add the following code. You'll need to replace secrets/values for your custom setting.

```yaml
################################################################################
#                                                                              #
#    V2G Liberty Configuration                                                 #
#    Contains all settings that need to be set for you, usually secrets        #
#    such as passwords, usernames, ip-addresses and entity addresses.          #
#                                                                              #
#    It is also used for storing variables for use in the app configuration.   #
#                                                                              #
#    After changes have been saved restart HA and AppDaemon.                   #
#                                                                              #
################################################################################

#############   BASIC HA CONFIG   ##############################################
## ALWAYS CHANGE ##
# Provide the coordinates of the location.
# Typical: lat. 52.xxxxxx,  lon. 4.xxxxxx, elevation in meters.
# ToDo: use these settings from Home Assistant instead
ha_latitude: xx.xxxxxxx
ha_longitude: x.xxxxxxx
ha_elevation: x
ha_time_zone: Europe/Amsterdam

# To which mobile device must (critical) platform notifications be sent.
# Can be found in the home assistant companion app under:
# Settings > Companion App > (Top item) your name and server > Device name
# Replace any spaces, minus (-), dots(.) with underscores (_)
admin_mobile_name: "your_device_name"
# Should be iOS or Android, others are not supported.
admin_mobile_platform: "your platform name: iOS or Android"

#############   FLEXMEASURES CONFIGURATION   ###################################

## ALWAYS CHANGE ##
fm_user_email: "your FM e-mail here (use quotes)"
fm_user_password: "your FM password here (use quotes)"

fm_account_power_sensor_id: XX
fm_account_availability_sensor_id: XX
fm_account_soc_sensor_id: XX
fm_account_cost_sensor_id: XX

# For electricity_provider the choices are:
#   nl_generic * †
#   no_generic * †
# Or one of the Dutch energy companies (VAT and markup are set in FlexMeasures):
#   nl_anwb_energie
#   nl_next_energy
#   nl_tibber
# If your energy company is missing, please let us know and we'll add it to the list.
# If you send your own prices (and emissions) data to FM through the API then use.
#   self_provided †
#
#  * In these cases it is assumed consumption and production price are the same.
#  † For these you can/should provide VAT and Markup (see further down).
electricity_provider: "nl_generic"

# How would you'd like the charging / discharging to be optimised?
# Choices are price or emission
fm_optimisation_mode: "price"

# For option "own-prices" the FM account has it's onw sensor_id's
fm_own_price_production_sensor_id: pp
fm_own_price_consumption_sensor_id: cc
fm_own_emissions_sensor_id: ee
fm_own_context_display_name: "Own Prices and Emissions"

# The "own price configuration" is meant to be "on the way to generic" but currently 
# specifically fits the Amber Electric integration. This integration populates
# entities XXX and YYY with forecast data
# This has the following structure:
# forecasts:
#   - duration: 30
#     date: "2024-03-23"
#     nem_date: "2024-03-23T08:00:00+10:00"
#     per_kwh: 0.09
#     spot_per_kwh: 0.09
#     start_time: "2024-03-22T21:30:01+00:00"
#     end_time: "2024-03-22T22:00:00+00:00"
#     renewables: 32
#     spike_status: none
#     descriptor: high
ha_sensor_id_own_consumption_price_forecast: "sensor.XXX"
ha_sensor_id_own_production_price_forecast: "sensor.YYY"
collection_name: "forecasts"
price_label: "per_kwh"
emission_label: "renewables"
uom_label: "unit_of_measurement"
start_label: "start_time"
end_label: "end_time"

# ****** Pricing data ********
# Pricing data only needs to be provided if a generic electricity provider is used
# For transforming the raw price data (from FM) to net price to be shown in UI.
# Calculation:
# (market_price_per_kwh + markup_per_kwh) * VAT

# Value Added Tax.
# This is only taken into account for electricity_providers marked with †
# Use a calculation factor (100 + VAT / 100).
# E.g. for NL VAT is 21%, so factor is 1.21. Use dot (.) not comma (,).
# If you'd like to effectively "not use VAT" you can set it to 1
VAT: 1.21

# Markup per kWh
# This is only taken into account for electricity_providers marked with †
# This usually includes energy tax and supplier markup
# Energy tax per kWh excluding VAT.
# Markup in €ct/kWh, Use dot (.) not comma (,).
# If you'd like to effectively "not use a markup" you can set it to 0
markup_per_kwh: 14.399


## VERY RARELY CHANGE ##
fm_base_entity_address: "ea1.2020-07.nl.seita.flexmeasures:fm1."
fm_base_entity_address_power: "ea1.2022-03.nl.seita.flexmeasures:fm1."
fm_base_entity_address_availability: "ea1.2022-03.nl.seita.flexmeasures:fm1."
fm_base_entity_address_soc: "ea1.2022-03.nl.seita.flexmeasures:fm1."

# This represents how far ahead the schedule should look. Keep at this setting.
fm_schedule_duration: "PT27H"

#############   CHARGER CONFIGURATION   ########################################

## ALWAYS CHANGE ##
# This usually is an IP address but can be a named URL as well.
evse_host: "your charger host here"
# Usually 502
evse_port: 502

## ALWAYS CHECK / SOME TIMES CHANGE ##
# Research shows the roundtrip efficient is around 85 % for a typical EV + charger.
# This number is taken into account when calculating the optimal schedule.
# Use an integer between 50 and 100.
charger_plus_car_roundtrip_efficiency: 85

#############   CAR & POWER-CONNECTION CONFIGURATION   #########################
## ALWAYS CHECK/CHANGE ##

# The usable energy storage capacity of the battery of the car, as an integer.
# For the Nissan Leaf this is usually 21, 39 or 59 (advertised as 24, 40 and 62).
# See https://ev-database.org.
# Use an integer between 10 and 200.
car_max_capacity_in_kwh: 59

# What would you like to be the minimum charge in your battery?
# The scheduling will not discharge below this value and if the car returns with
# and SoC below this value, the battery will be charged to this minimum asap
# before regular scheduling.
# A high value results in always having a greater driving range available, even
# when not planned, but less capacity available for dis-charge and so lesser
# earnings.
# A lower value results in sometimes a smaller driving range available for
# un-planned drives but there is always more capacity for discharge and so more
# earnings.
# Some research suggests battery life is shorter if min SoC is below 15%.
# In some cars the SoC sometimes skips a number, e.g. from 21 to 19%,
# skipping 20%. This might result in toggling charging behaviour around this
# minimum SoC. If this happens try a value 1 higher or lower.
# The setting must be an integer (without the % sign) between 10 and 30, default is 20.
car_min_soc_in_percent: 20

# What would you like to be the maximum charge in your car battery?
# The schedule will use this for regular scheduling. It can be used to further
# protect the battery from degradation as a 100% charge (for longer periods) may
# reduce battery health/lifetime.
# When a calendar item is present, the schedule will ignore this setting and
# try to charge to 100% (or if the calendar item has a target use that).
# A low setting reduces schedule flexibility and so the capability to earn
# money and reduce emissions.
# The setting must be an integer value between 60 and 100, default is 80.
car_max_soc_in_percent: 80

# When the car connects with a SoC higher than car_max_soc_in_percent
# how long may the schedule take to bring the SoC back to this maximum?
# A longer duration gives opportunity for higher gains but might have a (minor)
# degradation effect on the battery.
# This duration is excluding the (minimum) time it takes to get back to the
# desired maximum under normal cycling conditions.
# The setting must be an integer value between 2 and 36, default is 12.
allowed_duration_above_max_soc_in_hrs: 12

# What is the average electricity usage of your car in watt-hour (Wh) per km?
# In most cars you can find historical data in the menu's. Normally this is somewhere
# between 140 (very efficient!) and 300 (rather in-efficient vans).
# Make sure you use the right "unit of measure": Wh.
# The setting must be an integer value.
car_average_wh_per_km: 174

# Max (dis-)charge_power in Watt
#   Be safe:
#   Please consult a certified electrician what max power can be set on
#   the charger. Electric safety must be provided by the hardware. Limits for over
#   powering must be guarded by hardware.
#   This software should not be the only fail-safe.
#   It is recommended to use a load balancer.
#
# If a load balancer (power-boost for WB) is used:
# Set this to "Amperage setting in charger" * grid voltage.
# E.g. 25A * 230V = 5750W.
# If there is no load balancer in use, use a lower setting.
# Usually the discharge power is the same but in some cases the charger or
# (gird operator) regulations require a different (lower) dis-charge power.
evse_max_charging_power: XXXX
evse_max_discharging_power: XXXX

#############   CALENDAR CONFIGURATION   #######################################

# Configuration for the calendar for making reservations for the car #
# This is mandatory
# It can be any caldav calendar (NextCloud, OwnCloud, iCloud, Google, etc.) It is recommended to use caldav over the Google integration for ease of installation here.
car_calendar_name: calendar.car_reservation
# This normally matches the ha_time_zone setting.
car_calendar_timezone: Europe/Amsterdam

## Remove these if a none-caldav calendar via a HA integration is used.
## Please also remove the calendar related entities in v2g_liberty_package.yaml
caldavUN: "your caldav username here (use quotes)"
caldavPWD: "your caldav password here (use quotes)"
caldavURL: "your caldav URL here (use quotes)"

```


## Configure HA to use v2g-liberty

This (nearly last) step will combine the work you've done so far: it adds V2G Liberty to HA.
In your text editor add the following to the top of the `configuration.yaml` file:

```yaml
homeassistant:
  packages:
    v2g_pack: !include packages/v2g_liberty/v2g_liberty_package.yaml
```

### HA Settings

These are "out of the box" super handy HA features that are highly recommended.

#### Add additional users

This is optional but is highly recommended.
This lets all persons in the household operate the charger and they all get notified about relevant events (>80% charge etc.).

#### Install the HA companion app on your mobile

This is optional but highly recommended.
You can get it from the official app store of your phone platform.
If you’ve added your HA instance and logged in you can manage the charging via the app and, very conveniantly, receive notifications about the charging on you mobile.

#### Make V2G Liberty your default dashboard

After the restart (next step) you'll find the V2G Liberty dashboard in the sidebar. 
Probably underneath "Overview", which then likely is the current default dashboard. To make the V2G Liberty dashboard 
your default go to `Settings > Dashboards`. Select the V2G Liberty dashboard row and click the link "SET AS DEFAULT IN THIS DEVICE".



## Start it up
Now that so many files have changed/been added a restart of both Home Assistant and AppDaemon is needed.
HA can be restarted by `Settings > System > Restart (top right)`.
AppDaemon can be (re-)started via `Settings > Add-ons > AppDaemon > (Re-)start`.

Now the system needs 5 to 10 minutes before it runs nicely. If a car is connected you should see a schedule comming in soon after.

### Happy 🚘←⚡→🏡 charging!

<!-- <style 
  type="text/css">
  body {
    max-width: 50em;
    margin: 4em;
  }
  pre {
     max-height: 25em;
     overflow: auto;
  }
</style> -->
