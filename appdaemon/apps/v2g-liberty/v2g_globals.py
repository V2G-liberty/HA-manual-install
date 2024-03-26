from datetime import datetime, timedelta
import time

import appdaemon.plugins.hass.hassapi as hass

import constants as c


class V2GLibertyGlobals(hass.Hass):

    def initialize(self):
        self.log("Initializing V2GLibertyGlobals")

        c.CHARGER_PLUS_CAR_ROUNDTRIP_EFFICIENCY = self.read_and_process_int_setting(
            "charger_plus_car_roundtrip_efficiency", 50, 100) / 100
        self.log(f"v2g_globals roundtrip-efficiency: {c.CHARGER_PLUS_CAR_ROUNDTRIP_EFFICIENCY}.")

        # The MAX_(DIS)CHARGE_POWER constants migth be changed if the setting in the charge is lower 
        c.CHARGER_MAX_CHARGE_POWER = self.read_and_process_int_setting("charger_max_charging_power", 1380, 22000)
        self.log(f"v2g_globals max charge power: {c.CHARGER_MAX_CHARGE_POWER} Watt.")
        c.CHARGER_MAX_DISCHARGE_POWER = self.read_and_process_int_setting("charger_max_discharging_power", 1380, 22000)
        self.log(f"v2g_globals max dis-charge power: {c.CHARGER_MAX_DISCHARGE_POWER}.")

        c.CAR_MAX_CAPACITY_IN_KWH = self.read_and_process_int_setting("car_max_capacity_in_kwh", 10, 200)
        self.log(f"v2g_globals max-car-capacity: {c.CAR_MAX_CAPACITY_IN_KWH} kWh.")

        c.CAR_MIN_SOC_IN_PERCENT = self.read_and_process_int_setting("car_min_soc_in_percent", 10, 30)
        c.CAR_MIN_SOC_IN_KWH = c.CAR_MAX_CAPACITY_IN_KWH * c.CAR_MIN_SOC_IN_PERCENT / 100
        self.log(f"v2g_globals car-min-soc: {c.CAR_MIN_SOC_IN_PERCENT} % or {c.CAR_MIN_SOC_IN_KWH} kWh.")

        c.CAR_MAX_SOC_IN_PERCENT = self.read_and_process_int_setting("car_max_soc_in_percent", 60, 100)
        c.CAR_MAX_SOC_IN_KWH = c.CAR_MAX_CAPACITY_IN_KWH * c.CAR_MAX_SOC_IN_PERCENT / 100
        self.log(f"v2g_globals car-max-soc: {c.CAR_MAX_SOC_IN_PERCENT} % or {c.CAR_MAX_SOC_IN_KWH} kWh.")

        c.ALLOWED_DURATION_ABOVE_MAX_SOC = self.read_and_process_int_setting("allowed_duration_above_max_soc_in_hrs", 2, 36)
        self.log(f"v2g_globals allowed_duration_above_max_soc: {c.ALLOWED_DURATION_ABOVE_MAX_SOC} hrs.")

        c.FM_ACCOUNT_POWER_SENSOR_ID = int(float(self.args["fm_account_power_sensor_id"]))
        self.log(f"v2g_globals FM_ACCOUNT_POWER_SENSOR_ID: {c.FM_ACCOUNT_POWER_SENSOR_ID}.")
        c.FM_ACCOUNT_AVAILABILITY_SENSOR_ID = int(float(self.args["fm_account_availability_sensor_id"]))
        self.log(f"v2g_globals FM_ACCOUNT_AVAILABILITY_SENSOR_ID: {c.FM_ACCOUNT_AVAILABILITY_SENSOR_ID}.")
        c.FM_ACCOUNT_SOC_SENSOR_ID = int(float(self.args["fm_account_soc_sensor_id"]))
        self.log(f"v2g_globals FM_ACCOUNT_SOC_SENSOR_ID: {c.FM_ACCOUNT_SOC_SENSOR_ID}.")
        c.FM_ACCOUNT_COST_SENSOR_ID = int(float(self.args["fm_account_cost_sensor_id"]))
        self.log(f"v2g_globals FM_ACCOUNT_COST_SENSOR_ID: {c.FM_ACCOUNT_COST_SENSOR_ID}.")

        c.OPTIMISATION_MODE = self.args["fm_optimisation_mode"].strip().lower()
        self.log(f"v2g_globals OPTIMISATION_MODE: {c.OPTIMISATION_MODE}.")
        c.ELECTRICITY_PROVIDER = self.args["electricity_provider"].strip().lower()
        self.log(f"v2g_globals ELECTRICITY_PROVIDER: {c.ELECTRICITY_PROVIDER}.")

        # The utility provides the electricity, if the price and emissions data is provided to FM
        # by V2G Liberty this is labeled as "self_provided".
        if c.ELECTRICITY_PROVIDER == "self_provided":
            c.FM_PRICE_PRODUCTION_SENSOR_ID = int(float(self.args["fm_own_price_production_sensor_id"]))
            c.FM_PRICE_CONSUMPTION_SENSOR_ID = int(float(self.args["fm_own_price_consumption_sensor_id"]))
            c.FM_EMISSIONS_SENSOR_ID = int(float(self.args["fm_own_emissions_sensor_id"]))
            c.UTILITY_CONTEXT_DISPLAY_NAME = self.args["fm_own_context_display_name"]
        else:
            context = c.DEFAULT_UTILITY_CONTEXTS.get(
                c.ELECTRICITY_PROVIDER,
                c.DEFAULT_UTILITY_CONTEXTS["nl_generic"],
            )
            # ToDo: Notify user if fallback "nl_generic" is used..
            c.FM_PRICE_PRODUCTION_SENSOR_ID = context["production-sensor"]
            c.FM_PRICE_CONSUMPTION_SENSOR_ID = context["consumption-sensor"]
            c.FM_EMISSIONS_SENSOR_ID = context["emissions-sensor"]
            c.UTILITY_CONTEXT_DISPLAY_NAME = context["display-name"]
        self.log(f"v2g_globals FM_PRICE_PRODUCTION_SENSOR_ID: {c.FM_PRICE_PRODUCTION_SENSOR_ID}.")
        self.log(f"v2g_globals FM_PRICE_CONSUMPTION_SENSOR_ID: {c.FM_PRICE_CONSUMPTION_SENSOR_ID}.")
        self.log(f"v2g_globals FM_EMISSIONS_SENSOR_ID: {c.FM_EMISSIONS_SENSOR_ID}.")
        self.log(f"v2g_globals UTILITY_CONTEXT_DISPLAY_NAME: {c.UTILITY_CONTEXT_DISPLAY_NAME}.")

        self.log("Completed initializing V2GLibertyGlobals")

    def check_max_power_settings(self, max_charge_power: int):
        all_ok = True
        if c.CHARGER_MAX_CHARGE_POWER > max_charge_power:
            c.CHARGER_MAX_CHARGE_POWER = max_charge_power
            all_ok = False
        if c.CHARGER_MAX_DIS_CHARGE_POWER > max_charge_power:
            c.CHARGER_MAX_DIS_CHARGE_POWER = max_charge_power
            all_ok = False

        if not all_ok:
            message = f"The setting MAX_(DIS)CHARGE_POWER is lowered to stay within charger setting: '{max_charge_power}'."
            self.log(message)
            self.create_persistant_notification(
                title="Automatic configuration change",
                message=message,
                id="config_change_max_charge_power"
            )

    def create_persistant_notification(self, message:str, title:str, id:str):
        self.call_service(
            'persistent_notification/create',
            title=title,
            message=message,
            notification_id=id
        )


    def read_and_process_int_setting(self, setting_name: str, lower_limit: int, upper_limit: int) -> int:
        """Read and integer setting_name from HASS and guard the lower and upper limit"""
        try:
            reading = int(float(self.args[setting_name]))
        except:
            message = f"Error, the setting '{setting_name}' is not found in configuration files. V2G Liberty might not function correctly."
            self.log(message)
            id = "config_error_" + setting_name
            self.create_persistant_notification(
                title="Error in configuration",
                message=message,
                id=id
            )
            return None
        
        # Make sure this value is between lower_limit and upper_limit
        tmp = max(min(upper_limit, reading), lower_limit)
        if reading != tmp:
            message = f"The setting '{setting_name}' is changed from '{reading}' to '{tmp}' to stay within boundaries."
            self.log(message)
            id = "config_change_" + setting_name
            reading = tmp
            self.create_persistant_notification(
                title="Automatic configuration change",
                message=message,
                notification_id=id
            )
        return reading


def time_mod(time, delta, epoch=None):
    """From https://stackoverflow.com/a/57877961/13775459"""
    if epoch is None:
        epoch = datetime(1970, 1, 1, tzinfo=time.tzinfo)
    return (time - epoch) % delta


def time_round(time, delta, epoch=None):
    """From https://stackoverflow.com/a/57877961/13775459"""
    mod = time_mod(time, delta, epoch)
    if mod < (delta / 2):
        return time - mod
    return time + (delta - mod)


def time_ceil(time, delta, epoch=None):
    """From https://stackoverflow.com/a/57877961/13775459"""
    mod = time_mod(time, delta, epoch)
    if mod:
        return time + (delta - mod)
    return time
