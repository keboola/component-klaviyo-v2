import copy
import json
import logging
import warnings
from typing import List, Callable, Dict

import dateparser
from keboola.component.base import ComponentBase, sync_action
from keboola.component.dao import TableDefinition
from keboola.component.exceptions import UserException
from keboola.component.sync_actions import ValidationResult, MessageType, SelectElement
from keboola.csvwriter import ElasticDictWriter
from keboola.utils import header_normalizer

from client import KlaviyoClient, KlaviyoClientException
from json_parser import FlattenJsonParser

KEY_API_TOKEN = "#api_token"

KEY_OBJECTS = "objects"

KEY_TIME_RANGE_SETTINGS = "time_range_settings"
KEY_DATE_FROM = "date_from"
KEY_DATE_TO = "date_to"

KEY_CATALOGS_SETTINGS = "catalogs_settings"
KEY_CATALOGS_SETTINGS_FETCH_CATALOG_CATEGORIES = "fetch_catalog_categories"

KEY_CAMPAIGNS_SETTINGS = "campaigns_settings"
KEY_CAMPAIGNS_SETTINGS_FETCH_CAMPAIGN_CHANNELS = "fetch_campaign_channels"

KEY_EVENTS_SETTINGS = "events_settings"

KEY_PROFILES_SETTINGS = "profiles_settings"
KEY_PROFILES_SETTINGS_FETCH_PROFILES_MODE = "fetch_profiles_mode"
KEY_PROFILES_SETTINGS_FETCH_BY_LIST = "fetch_profiles_by_list"
KEY_PROFILES_SETTINGS_FETCH_BY_SEGMENT = "fetch_profiles_by_segment"

KEY_METRIC_AGGREGATES_SETTINGS = "metric_aggregates_settings"
KEY_METRIC_AGGREGATES_SETTINGS_METRIC_IDS = "metric_aggregates_ids"
KEY_METRIC_AGGREGATES_SETTINGS_INTERVAL = "metric_aggregates_interval"
KEY_METRIC_AGGERGATES_SETTING_BY = 'metric_aggregates_partitioning_by'

KEY_STORE_NESTED_ATTRIBUTES = "store_nested_attributes"

REQUIRED_PARAMETERS = [KEY_API_TOKEN, KEY_OBJECTS]
REQUIRED_IMAGE_PARS = []

OBJECT_ENDPOINTS = ["campaigns", "flows", "templates", "catalogs", "events", "metrics",
                    "lists", "segments", "profiles", "metric_aggregates"]

# Ignore dateparser warnings regarding pytz
warnings.filterwarnings(
    "ignore",
    message="The localize method is no longer necessary, as this time zone supports the fold attribute",
)

DEFAULT_DATE_FROM = "1990-01-01"


class Component(ComponentBase):

    def __init__(self):
        self.endpoint_func_mapping = {
            "campaigns": self.get_campaigns,
            "catalogs": self.get_catalogs,
            "events": self.get_events,
            "metrics": self.get_metrics,
            "lists": self.get_lists,
            "segments": self.get_segments,
            "profiles": self.get_profiles,
            "flows": self.get_flows,
            "templates": self.get_templates,
            "metric_aggregates": self.get_metric_aggregates
        }
        self.client = None
        self.result_writers = {}
        self.state = {}
        self.new_state = {}
        self.store_nested_attributes = False
        super().__init__()

    def run(self):
        import os
        a1 = os.environ.get('KBC_STACKID')
        a2 = os.environ.get('KBC_DATA_TYPE_SUPPORT')
        logging.info(f"{a1} - {a2}")
        self.validate_configuration_parameters(REQUIRED_PARAMETERS)
        self.validate_image_parameters(REQUIRED_IMAGE_PARS)

        self.state = self.get_state_file()
        self.new_state = copy.deepcopy(self.state)
        self.new_state["last_run"] = self._parse_date("now")

        params = self.configuration.parameters
        self.store_nested_attributes = params.get(KEY_STORE_NESTED_ATTRIBUTES, False)

        self._init_client()
        self._validate_user_parameters()

        objects = params.get(KEY_OBJECTS)

        for object_name in OBJECT_ENDPOINTS:
            if objects.get(object_name):
                logging.info(f"Fetching data of {object_name}")
                self.endpoint_func_mapping[object_name]()

        self._close_all_result_writers()
        self.write_state_file(self.new_state)

    def _init_client(self):
        params = self.configuration.parameters
        api_token = params.get(KEY_API_TOKEN)
        self.client = KlaviyoClient(api_token=api_token)

    def fetch_and_write_object_data(self, object_name: str, data_generator: Callable, **data_generator_kwargs) -> None:
        self._initialize_result_writer(object_name)
        parser = FlattenJsonParser()

        extra_data = {}
        for arg_name in data_generator_kwargs:
            if "_id" in arg_name:
                extra_data = {arg_name: data_generator_kwargs[arg_name]}

        for i, page in enumerate(data_generator(**data_generator_kwargs)):
            if i > 0 and i % 100 == 0:
                logging.info(f"Already fetched {i} pages of data of object {object_name}")

            for item in page:

                if self.store_nested_attributes:
                    parsed_attributes = item["attributes"]
                else:
                    parsed_attributes = parser.parse_row(item["attributes"])

                row = {"id": item["id"], **parsed_attributes, **extra_data}

                self._get_result_writer(object_name).writerow(row)

    def _add_columns_from_state_to_table_definition(self, object_name: str,
                                                    table_definition: TableDefinition) -> TableDefinition:
        if object_name in self.state:
            all_columns = table_definition.column_names
            for column in self.state.get(object_name):
                if column not in all_columns:
                    all_columns.append(column)
            table_definition.schema = all_columns
        return table_definition

    def get_metrics(self) -> None:
        self.fetch_and_write_object_data("metric", self.client.get_metrics)

    def get_lists(self) -> None:
        self.fetch_and_write_object_data("list", self.client.get_lists)

    def get_segments(self) -> None:
        self._initialize_result_writer("segment")

        for batch in self.client.get_segments(fields_segment=["name", "definition"]):
            for item in batch:
                name = item["attributes"].get("name")
                definition = item["attributes"].get("definition")
                self._get_result_writer("segment").writerow({"id": item["id"], "name": name, "definition": definition})

    def get_catalogs(self) -> None:
        self.fetch_and_write_object_data("catalog_item", self.client.get_catalog_items)

        catalog_settings = self.configuration.parameters.get(KEY_CATALOGS_SETTINGS)
        if catalog_settings.get(KEY_CATALOGS_SETTINGS_FETCH_CATALOG_CATEGORIES):
            self.fetch_and_write_object_data("catalog_categories", self.client.get_catalog_categories)

    def get_campaigns(self) -> None:
        channels = self.configuration.parameters.get(KEY_CAMPAIGNS_SETTINGS, ["email", "sms"])

        self._initialize_result_writer("campaign")
        self._initialize_result_writer("campaign_audience")
        self._initialize_result_writer("campaign_excluded_audience")
        parser = FlattenJsonParser()

        for channel in channels:
            for batch in self.client.get_campaigns(channel=channel):
                for item in batch:
                    audiences = item.get("attributes").pop("audiences")
                    included_audiences = audiences.get("included")
                    excluded_audiences = audiences.get("excluded")

                    self.get_campaign_messages(campaign_id=item["id"])

                    for included_audience in included_audiences:
                        self._get_result_writer("campaign_audience").writerow(
                            {"campaign_id": item["id"], "list_id": included_audience})
                    for excluded_audiences in excluded_audiences:
                        self._get_result_writer("campaign_excluded_audience").writerow(
                            {"campaign_id": item["id"], "list_id": excluded_audiences})

                    parsed_attributes = parser.parse_row(item["attributes"])
                    self._get_result_writer("campaign").writerow({"id": item["id"], **parsed_attributes})

    def get_campaign_messages(self, campaign_id: str) -> None:
        self._initialize_result_writer("campaign_message")
        parser = FlattenJsonParser()

        for batch in self.client.get_campaign_messages(campaign_id=campaign_id):
            for item in batch:
                parsed_attributes = parser.parse_row(item["attributes"])
                self._get_result_writer("campaign_message").writerow({"campaign_id": campaign_id, **parsed_attributes})

    def get_events(self) -> None:
        params = self.configuration.parameters
        event_settings = params.get(KEY_EVENTS_SETTINGS)
        time_range_setting = params.get(KEY_TIME_RANGE_SETTINGS)

        if time_range_setting:
            from_timestamp = self._parse_date(time_range_setting.get(KEY_DATE_FROM))
            to_timestamp = self._parse_date(time_range_setting.get(KEY_DATE_TO))
        # Stay here bacause for backward compatibility
        else:
            from_timestamp = self._parse_date(event_settings.get(KEY_DATE_FROM))
            to_timestamp = self._parse_date(event_settings.get(KEY_DATE_TO))

        self.fetch_and_write_object_data("event", self.client.get_events,
                                         from_timestamp_value=from_timestamp,
                                         to_timestamp_value=to_timestamp)

    def get_profiles(self) -> None:
        params = self.configuration.parameters
        profile_settings = params.get(KEY_PROFILES_SETTINGS)
        fetch_profiles_mode = profile_settings.get(KEY_PROFILES_SETTINGS_FETCH_PROFILES_MODE)

        if fetch_profiles_mode == "fetch_all":
            self.fetch_and_write_object_data("profile", self.client.get_profiles)

        elif fetch_profiles_mode == "fetch_by_segment":
            segments = profile_settings.get(KEY_PROFILES_SETTINGS_FETCH_BY_SEGMENT, [])
            for segment_id in segments:
                self.fetch_and_write_object_data("segment_profile", self.client.get_segment_profiles,
                                                 segment_id=segment_id)

        elif fetch_profiles_mode == "fetch_by_list":
            lists = profile_settings.get(KEY_PROFILES_SETTINGS_FETCH_BY_LIST, [])
            for list_id in lists:
                self.fetch_and_write_object_data("list_profile", self.client.get_list_profiles, list_id=list_id)

    def get_flows(self) -> None:
        self.fetch_and_write_object_data("flow", self.client.get_flows)

    def get_templates(self) -> None:
        self.fetch_and_write_object_data("template", self.client.get_templates)

    def get_metric_aggregates(self) -> None:
        params = self.configuration.parameters
        metric_aggregates_settings = params.get(KEY_METRIC_AGGREGATES_SETTINGS)

        time_range_settings = params.get(KEY_TIME_RANGE_SETTINGS)
        interval = metric_aggregates_settings.get(KEY_METRIC_AGGREGATES_SETTINGS_INTERVAL)
        from_timestamp = self._parse_date(time_range_settings.get(KEY_DATE_FROM))
        to_timestamp = self._parse_date(time_range_settings.get(KEY_DATE_TO))
        ids = metric_aggregates_settings.get(KEY_METRIC_AGGREGATES_SETTINGS_METRIC_IDS)
        by = metric_aggregates_settings.get(KEY_METRIC_AGGERGATES_SETTING_BY)

        for id in ids:
            self.fetch_and_write_object_data(
                "metric_aggregates",
                self.client.query_metric_aggregates,
                metric_id=id,
                interval=interval,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                by=by
                )

    def _parse_date(self, date_to_parse: str) -> int:
        if date_to_parse.lower() in {"last", "lastrun", "last run"}:
            # remove 1 hour / 3600s so there is no issue if data is being downloaded at the same time an object is
            # being inserted/ being updated
            return int(self.state.get("last_run", int(dateparser.parse(DEFAULT_DATE_FROM).timestamp()))) - 3600
        try:
            parsed_timestamp = int(dateparser.parse(date_to_parse).timestamp())
        except (AttributeError, TypeError) as err:
            raise UserException(f"Failed to parse date '{date_to_parse}', make sure the date is either in YYYY-MM-DD "
                                f"format or relative date i.e. 5 days ago, 1 month ago, yesterday, etc.") from err
        return parsed_timestamp

    def _initialize_result_writer(self, object_name: str) -> None:
        if object_name not in self.result_writers:
            table_schema = self.get_table_schema_by_name(object_name)
            table_definition = self.create_out_table_definition_from_schema(table_schema, incremental=True)
            table_definition = self._add_columns_from_state_to_table_definition(object_name, table_definition)
            writer = ElasticDictWriter(table_definition.full_path, table_definition.column_names)
            self.result_writers[object_name] = {"table_definition": table_definition, "writer": writer}

    def _get_result_writer(self, object_name: str) -> ElasticDictWriter:
        return self.result_writers.get(object_name).get("writer")

    def _close_all_result_writers(self) -> None:
        res_writers = ""
        for i in self.result_writers:
            x = self.result_writers.get(i).get("table_definition")
            res_writers += x.name
            res_writers += "-"
        logging.info(f"Res writers: {res_writers}")
        for object_name in self.result_writers:
            writer = self._get_result_writer(object_name)
            table_definition = self.result_writers.get(object_name).get("table_definition")
            writer.close()
            self.new_state[object_name] = copy.deepcopy(writer.fieldnames)

            logging.info(f"1 {table_definition.column_names}")
            writer_columns = copy.deepcopy(writer.fieldnames)
            logging.info(f"2 {table_definition.column_names}")
            table_definition = self._deduplicate_column_names_and_metadata(table_definition, writer_columns)
            table_definition = self._add_missing_metadata(table_definition)
            logging.info(f"3 {table_definition.column_names}")

            deduped_columns = table_definition.column_names.copy()
            normalized_headers = self._normalize_headers(deduped_columns)
            logging.info(f"4 {normalized_headers}")
            table_definition.schema = normalized_headers

            self.write_manifest(table_definition)

    def _add_missing_metadata(self, table_definiton: TableDefinition) -> TableDefinition:
        logging.info(f"Adding missing for {table_definiton.name} - \
                     {table_definiton.columns} - {table_definiton.column_names}")
        logging.info(f"{table_definiton.table_metadata.column_metadata}")
        for column in table_definiton.column_names:
            if column not in table_definiton.table_metadata.column_metadata.keys():
                table_definiton.table_metadata.column_metadata[column] = {
                    'KBC.description': '',
                    'KBC.datatype.basetype': 'STRING',
                    'KBC.datatype.nullable': True}
                logging.warning(f"Creating dummy metadata for column {column}")
        return table_definiton

    @staticmethod
    def _normalize_headers(columns: List[str]) -> List[str]:
        head_norm = header_normalizer.get_normalizer(strategy=header_normalizer.NormalizerStrategy.ENCODER,
                                                     char_encoder="unicode")
        return head_norm.normalize_header(columns)

    def _deduplicate_column_names_and_metadata(self, table_definition: TableDefinition,
                                               columns: List[str]) -> TableDefinition:
        """
            Method to update duplicate columns and their metadata.
            Klaviyo allows duplicate column names when the case is different
            e.g. columns property_name and property_Name are 2 valid distinct data columns. In Keboola, this leads to
            a duplicate column error, and we must rename the columns to property_name and property_Name_2 in this
            case.
        """
        final_columns = []
        column_count = {}
        for column in columns:
            # keboola_column_name is the resulting column name in Keboola, no spaces, and lowercase.
            # Lowercase because Keboola takes column name Product and product as the same.
            keboola_column_name = column.lower().replace(" ", "_")
            column_name = column
            if keboola_column_name not in column_count:
                column_count[keboola_column_name] = 1
            else:
                column_count[keboola_column_name] += 1
                column_name = f"{column_name}_{column_count[keboola_column_name]}"
                # If column metadata is present we must update the metadata information as well.
                table_definition.table_metadata.column_metadata = self.swap_key(
                    table_definition.table_metadata.column_metadata, column,
                    column_name)
            final_columns.append(column_name)
        table_definition.schema = final_columns
        return table_definition

    @staticmethod
    def swap_key(dictionary: Dict, old_key: str, new_key: str) -> Dict:
        if old_key in dictionary:
            dictionary[new_key] = dictionary.pop(old_key)
        return dictionary

    def _validate_user_parameters(self) -> None:
        params = self.configuration.parameters
        objects = params.get(KEY_OBJECTS)
        events = objects.get("events")
        metric_aggregates = objects.get("metric_aggregates")

        # Old version of time range, kept for backward compatibility
        # Validate Date From and Date for events, if events are to be downloaded
        event_settings = params.get(KEY_EVENTS_SETTINGS)
        if event_settings and events:
            logging.info("Validating Event parameters...")
            self._parse_date(event_settings.get(KEY_DATE_FROM))
            self._parse_date(event_settings.get(KEY_DATE_TO))
            logging.info("Event parameters are valid")

        # Validate Date From and Date for time ranged endpoints
        time_range_setting = params.get(KEY_TIME_RANGE_SETTINGS)
        if (events or metric_aggregates) and time_range_setting:
            logging.info("Validating Date range parameters...")
            self._parse_date(time_range_setting.get(KEY_DATE_FROM))
            self._parse_date(time_range_setting.get(KEY_DATE_TO))
            logging.info("Date range parameters are valid")

        # Validate if segment ids for profile fetching are valid
        profile_settings = params.get(KEY_PROFILES_SETTINGS, {})
        profile_mode = profile_settings.get(KEY_PROFILES_SETTINGS_FETCH_PROFILES_MODE)
        if profile_mode == "fetch_by_segment" and objects.get("profiles"):
            logging.info("Validating Profile fetching parameters...")
            segments = profile_settings.get(KEY_PROFILES_SETTINGS_FETCH_BY_SEGMENT, [])
            for segment_id in segments:
                try:
                    self.client.get_segment(segment_id)
                except KlaviyoClientException as e:
                    raise UserException(f"Segment with ID {segment_id} not found.") from e
            logging.info("Profile fetching parameters are valid")

        # Validate if list ids for profile fetching are valid
        if profile_mode == "fetch_by_list" and objects.get("profiles"):
            logging.info("Validating Profile fetching parameters...")
            lists = profile_settings.get(KEY_PROFILES_SETTINGS_FETCH_BY_LIST, [])
            for list_id in lists:
                self.client.get_list(list_id)
            logging.info("Profile fetching parameters are valid")

        # Validate if list ids for metric aggregates are valid
        metric_aggregates_settings = params.get(KEY_METRIC_AGGREGATES_SETTINGS)
        if metric_aggregates_settings and metric_aggregates:
            metric_aggregates_ids = metric_aggregates_settings.get(KEY_METRIC_AGGREGATES_SETTINGS_METRIC_IDS)
            logging.info("Validating metric aggregates parametrs...")
            for metric_id in metric_aggregates_ids:
                try:
                    self.client.get_metric(metric_id)
                except KlaviyoClientException as e:
                    raise UserException(f"Metric with ID {metric_id} not found.") from e
            logging.info("Metric aggregates parametrs are valid")
        # sync action that is executed when configuration.json "action":"testConnection" parameter is present.

    @sync_action('validate_connection')
    def test_connection(self) -> ValidationResult:
        self._init_client()
        credentials_valid, missing_scopes, last_exception = self.client.test_credentials()

        result = ValidationResult("Credentials are valid!", MessageType.SUCCESS)

        if not credentials_valid:
            result = ValidationResult(
                "The provided API token is invalid. Unauthorized.",
                MessageType.DANGER)

        elif missing_scopes:
            scope_rows = "\n".join([f'| {scope} | {detail} |' for scope, detail in missing_scopes.items()])
            missing_scopes_str = f'| Scope | Error |\n|-------|-------|\n{scope_rows}'

            result = ValidationResult(
                "The provided token is valid but some scopes are unauthorized. "
                "Please enable RO for following scopes or fix related issues: \n\n"
                f"{missing_scopes_str}"
                "\n\nFor more information refer to [the documentation](https://help.klaviyo.com/"
                "hc/en-us/articles/7423954176283#add-a-scope-to-a-private-api-key-2)",
                MessageType.WARNING)

        return result

    @sync_action("loadListIds")
    def load_list_ids(self) -> List[SelectElement]:
        self._init_client()
        try:
            list_ids = self.client.get_list_ids()
            r = [SelectElement(value=list_id.get("id"), label=json.dumps(list_id.get("name"))) for list_id in list_ids]
        except Exception as e:
            raise UserException(e) from e
        return r

    @sync_action("loadSegmentIds")
    def load_segment_ids(self) -> List[SelectElement]:
        self._init_client()
        try:
            segment_ids = self.client.get_segment_ids()
            r = [SelectElement(value=segment_id.get("id"), label=json.dumps(segment_id.get("name")))
                 for segment_id in segment_ids]
        except Exception as e:
            raise UserException(e) from e
        return r

    @sync_action("loadMetricIds")
    def load_metric_ids(self) -> List[SelectElement]:
        self._init_client()
        try:
            metric_ids = self.client.get_metric_ids()
            r = [SelectElement(value=metric_id.get("id"), label=json.dumps(metric_id.get("name")))
                 for metric_id in metric_ids]
        except Exception as e:
            raise UserException(e) from e
        return r


if __name__ == "__main__":
    try:
        # import os
        # os.environ['KBC_DATA_TYPE_SUPPORT'] = 'none'
        # os.environ['KBC_STACKID'] = "connection.keboola.com"
        comp = Component()
        # this triggers the run method by default and is controlled by the configuration.action parameter
        comp.execute_action()
    except KlaviyoClientException as exc:
        logging.exception(exc)
        exit(1)
    except UserException as exc:
        logging.exception(exc)
        exit(1)
    except Exception as exc:
        logging.exception(exc)
        exit(2)
