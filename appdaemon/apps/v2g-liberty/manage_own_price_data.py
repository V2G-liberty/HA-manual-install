from datetime import datetime, timedelta
import isodate
import time
import json
import math
import requests
import constants as c
from typing import List, Union
import appdaemon.plugins.hass.hassapi as hass
from v2g_globals import time_round, convert_to_duration_string

class ManageOwnPriceData(hass.Hass):
    """
    App reads data from the entities that the integration of the power-company populates.

    It is expected that there are:
    Forecast entities for consumption- and production prices per kWh for fixed intervals in
    a longer period ahead (e.g. 12 or 24 hrs). These also include an indication of the
    % renewables:
    The data is expected to have the following structure:
    forecasts:
      - per_kwh: 0.09
        renewables: 32
        start_time: "2024-03-22T21:30:01+00:00"
        end_time: "2024-03-22T22:00:00+00:00"
    """

    FM_ENTITY_PRICE_PRODUCTION: str
    FM_ENTITY_PRICE_CONSUMPTION: str
    FM_ENTITY_EMISSIONS: str

    # The sensor (or entity) id's to which the third party integration
    # writes the Consumption- and Production Price (Forecasts)
    HA_CPF_SENSOR_ID: str
    HA_PPF_SENSOR_ID: str

    # The data in foregoing constants has the following structure:
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
    # To extract the right data the following constants are used.
    COLLECTION_NAME: str
    PRICE_LABEL: str
    EMISSION_LABEL: str
    UOM_LABEL: str  # currently un-used because Amber does not use the TLA but the general
    START_LABEL: str
    END_LABEL: str

    RESOLUTION_TIMEDELTA: datetime

    POLLING_INTERVAL_SECONDS: int
    TZ: datetime
    CURRENCY: str = "AUD"

    KWH_MWH_FACTOR:int = 1000

    last_consumption_prices: list = []
    last_production_prices: list = []
    last_emissions: list = []

    poll_timer_handle: object

    fm_data_handler: object
    v2g_main_app: object

    async def initialize(self):
        self.log(f"Initializing ManageOwnPriceData...")

        # TODO:
        # This can only be done if sensors in FM have been made.
        if c.ELECTRICITY_PROVIDER != "self_provided":
            self.log(f"Not loading manage_own_price_data module as electricity provider is not 'self_provided'.")
            return

        self.TZ = isodate.parse_tzinfo(self.get_timezone())

        # TODO: get currency from HA.
        
        self.RESOLUTION_TIMEDELTA = timedelta(minutes=c.FM_EVENT_RESOLUTION_IN_MINUTES)
        self.POLLING_INTERVAL_SECONDS = c.FM_EVENT_RESOLUTION_IN_MINUTES * 60

        self.HA_CPF_SENSOR_ID = self.args["ha_sensor_id_own_consumption_price_forecast"]
        self.HA_PPF_SENSOR_ID = self.args["ha_sensor_id_own_production_price_forecast"]

        self.COLLECTION_NAME = self.args["collection_name"]
        self.PRICE_LABEL = self.args["price_label"]
        self.EMISSION_LABEL = self.args["emission_label"]
        #self.UOM_LABEL = self.args["uom_label"]
        self.START_LABEL = self.args["start_label"]
        self.END_LABEL = self.args["end_label"]
        
        b = self.args["fm_base_entity_address"]
        self.FM_ENTITY_PRICE_PRODUCTION = b + str(c.FM_PRICE_PRODUCTION_SENSOR_ID)
        self.FM_ENTITY_PRICE_CONSUMPTION = b + str(c.FM_PRICE_CONSUMPTION_SENSOR_ID)
        self.FM_ENTITY_EMISSIONS = b + str(c.FM_EMISSIONS_SENSOR_ID)

        self.fm_data_handler = await self.get_app("set_fm_data")
        self.v2g_main_app = await self.get_app("v2g_liberty")

        # TODO: remove test code
        self.poll_timer_handle = await self.run_every(self.__check_for_price_changes, "now+1", self.POLLING_INTERVAL_SECONDS)
        # self.poll_timer_handle = await self.run_every(self.__check_for_price_changes, "now", 30)

        self.log(f"Completed Initializing ManageOwnPriceData.")


    def parse_to_rounded_local_datetime(self, date_time: str) -> datetime:
        # self.log(f"parse_to_rounded_local_datetime, original: {date_time}.")
        date_time = date_time.replace(" ", "T")
        date_time = isodate.parse_datetime(date_time).astimezone(self.TZ)
        date_time = time_round(date_time, self.RESOLUTION_TIMEDELTA)
        # self.log(f"parse_to_rounded_local_datetime, with  TZ: {date_time.isoformat()}.")
        return date_time


    async def __check_for_price_changes(self, kwargs):
        """ Checks if prices have changed.
            To be called every 5 minutes. Not on change events of price sensors, these are to volatile.
            If any changes:
            + Send changed prices and/or emissions to FM
            + Request a new schedule
        """
        new_schedule_needed = False

        #### Consumption prices (& emissions) ####
        consumption_prices = []
        emissions = []

        state = await self.get_state(self.HA_CPF_SENSOR_ID, attribute="all")
        collection_cpf = state["attributes"][self.COLLECTION_NAME]
        for item in collection_cpf:
            consumption_prices.append(round(float(item[self.PRICE_LABEL]) * self.KWH_MWH_FACTOR, 2))
            # Emissions are same for consumption- and production prices so only done here.
            # Amber has % renewables, FlexMeasures uses % emissions as it runs a cost minimisation.
            # So, emissions % = 100 - renewables %.
            emissions.append(100 - int(float(item[self.EMISSION_LABEL])))

        if consumption_prices != self.last_consumption_prices:
            self.log("__check_for_price_changes: consumption_prices changed")
            start_cpf = self.parse_to_rounded_local_datetime(collection_cpf[0][self.START_LABEL])
            end_cpf = self.parse_to_rounded_local_datetime(collection_cpf[-1][self.END_LABEL])
            duration_cpf = int(float(((end_cpf - start_cpf).total_seconds()/60)))
            duration_cpf = convert_to_duration_string(duration_cpf)
            self.last_consumption_prices = list(consumption_prices)
            uom = f"{self.CURRENCY}/MWh"
            res = self.fm_data_handler.post_data(
                fm_sensor_id = self.FM_ENTITY_PRICE_CONSUMPTION, 
                values = consumption_prices,
                start = start_cpf,
                duration = duration_cpf,
                uom = uom
            )
            if res and c.OPTIMISATION_MODE == "price":
                new_schedule_needed = True
            self.log(f"__check_for_price_changes, res: {res}, "
                     f"opt_mod: {c.OPTIMISATION_MODE}, new_schedule: {new_schedule_needed}")
 
        if emissions != self.last_emissions:
            self.log("__check_for_price_changes: emissions changed")
            # TODO: copied code from previous block, please prevent this.
            start_cpf = self.parse_to_rounded_local_datetime(collection_cpf[0][self.START_LABEL])
            end_cpf = self.parse_to_rounded_local_datetime(collection_cpf[-1][self.END_LABEL])
            duration_cpf = int(float(((end_cpf - start_cpf).total_seconds()/60)))  # convert sec. to min.
            duration_cpf = convert_to_duration_string(duration_cpf)
            self.last_emissions = list(emissions)
            uom = "%"
            res = self.fm_data_handler.post_data(
                fm_sensor_id = self.FM_ENTITY_EMISSIONS, 
                values = emissions,
                start = start_cpf,
                duration = duration_cpf,
                uom = uom
            )
            if res and c.OPTIMISATION_MODE != "price":
                new_schedule_needed = True
            self.log(f"__check_for_price_changes, res: {res}, "
                     f"opt_mod: {c.OPTIMISATION_MODE}, new_schedule: {new_schedule_needed}")

        #### Production prices ####
        production_prices = []
        state = await self.get_state(self.HA_PPF_SENSOR_ID, attribute="all")
        collection_ppf = state["attributes"][self.COLLECTION_NAME]
        for item in collection_ppf:
            production_prices.append(round(float(item[self.PRICE_LABEL]) * self.KWH_MWH_FACTOR, 2))

        if production_prices != self.last_production_prices:
            self.log("__check_for_price_changes: production_prices changed")
            self.last_production_prices = list(production_prices)
            start_ppf = self.parse_to_rounded_local_datetime(collection_ppf[0][self.START_LABEL])
            end_ppf = self.parse_to_rounded_local_datetime(collection_ppf[-1][self.END_LABEL])
            duration_ppf = int(float(((end_ppf - start_ppf).total_seconds()/60)))
            duration_ppf = convert_to_duration_string(duration_ppf)
            uom = f"{self.CURRENCY}/MWh"
            res = self.fm_data_handler.post_data(
                fm_sensor_id = self.FM_ENTITY_PRICE_PRODUCTION, 
                values = production_prices,
                start = start_ppf,
                duration = duration_ppf,
                uom = uom
            )
            if res and (c.OPTIMISATION_MODE == "price"):
                new_schedule_needed = True
            self.log(f"__check_for_price_changes, res: {res}, opt_mod: {c.OPTIMISATION_MODE}, new_schedule: {new_schedule_needed}")
        
        if not new_schedule_needed:
            self.log("__check_for_price_changes: not any changes")
            return

        msg=f"new own {c.OPTIMISATION_MODE}s"
        await self.v2g_main_app.trigger_set_next_action(v2g_args=msg)




