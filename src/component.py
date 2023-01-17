import logging
import copy
import dateparser
import warnings

from typing import List, Callable

from keboola.csvwriter import ElasticDictWriter
from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException
from keboola.component.dao import TableDefinition
from keboola.utils.helpers import comma_separated_values_to_list

from client import KlaviyoClient
from json_parser import FlattenJsonParser

KEY_API_TOKEN = "#api_token"

KEY_OBJECTS = "objects"

KEY_DATE_FROM = "date_from"
KEY_DATE_TO = "date_to"

KEY_CAMPAIGNS_SETTINGS = "campaigns_settings"
KEY_CAMPAIGNS_SETTINGS_FETCH_CAMPAIGN_RECIPIENTS = "fetch_campaign_recipients"

KEY_CATALOGS_SETTINGS = "catalogs_settings"
KEY_CATALOGS_SETTINGS_FETCH_CATALOG_CATEGORIES = "fetch_catalog_categories"

KEY_EVENTS_SETTINGS = "events_settings"

KEY_FLOWS_SETTINGS = "flows_settings"

KEY_PROFILES_SETTINGS = "profiles_settings"
KEY_PROFILES_SETTINGS_FETCH_PROFILES_MODE = "fetch_profiles_mode"
KEY_PROFILES_SETTINGS_FETCH_BY_LIST = "fetch_by_list"
KEY_PROFILES_SETTINGS_FETCH_BY_SEGMENT = "fetch_by_segment"

REQUIRED_PARAMETERS = [KEY_API_TOKEN, KEY_OBJECTS]
REQUIRED_IMAGE_PARS = []

# "flows" object endpoint is disfunctional for the time being
# "templates" object endpoint is disfunctional for the time being
OBJECT_ENDPOINTS = ["campaigns", "catalogs", "events", "metrics",
                    "lists", "segments", "profiles"]

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
            "profiles": self.get_profiles
            # "flows": self.get_flows,
            # "templates": self.get_templates
        }
        self.client = None
        self.result_writers = {}
        self.state = {}
        self.new_state = {}
        super().__init__()

    def run(self):
        self.validate_configuration_parameters(REQUIRED_PARAMETERS)
        self.validate_image_parameters(REQUIRED_IMAGE_PARS)

        self.state = self.get_state_file()
        self.new_state = copy.deepcopy(self.state)
        self.new_state["last_run"] = self._parse_date("now")

        params = self.configuration.parameters

        # TODO Validate event date from and date to, and other things before downloading data. Fail first
        # TODO Normalize_column_names

        api_token = params.get(KEY_API_TOKEN)
        self.client = KlaviyoClient(api_token=api_token)

        objects = params.get(KEY_OBJECTS)

        for object_name in OBJECT_ENDPOINTS:
            if objects.get(object_name):
                logging.info(f"Fetching data of {object_name}")
                self.endpoint_func_mapping[object_name]()

        self._close_all_result_writers()
        self.write_state_file(self.new_state)

    def fetch_and_write_object_data(self, object_name: str, data_generator: Callable,
                                    **data_generator_kwargs) -> None:
        self._initialize_result_writer(object_name)
        parser = FlattenJsonParser()
        for i, page in enumerate(data_generator(**data_generator_kwargs)):
            if i > 0 and i % 100 == 0:
                logging.info(f"Already fetched {i} pages of data of object {object_name}")
            for item in page:
                parsed_attributes = parser.parse_row(item["attributes"])
                self._get_result_writer(object_name).writerow({"id": item["id"], **parsed_attributes})

    def _add_columns_from_state_to_table_definition(self, object_name: str,
                                                    table_definition: TableDefinition) -> TableDefinition:
        if object_name in self.state:
            all_columns = table_definition.columns
            for column in self.state.get(object_name):
                if column not in all_columns:
                    all_columns.append(column)
            table_definition.columns = all_columns
        return table_definition

    def get_metrics(self) -> None:
        self.fetch_and_write_object_data("metric", self.client.get_metrics)

    def get_lists(self) -> None:
        self.fetch_and_write_object_data("list", self.client.get_lists)

    def get_segments(self) -> None:
        self.fetch_and_write_object_data("segment", self.client.get_segments)

    def get_catalogs(self) -> None:
        self.fetch_and_write_object_data("catalog_item", self.client.get_catalog_items)

        catalog_settings = self.configuration.parameters.get(KEY_CATALOGS_SETTINGS)
        if catalog_settings.get(KEY_CATALOGS_SETTINGS_FETCH_CATALOG_CATEGORIES):
            self.fetch_and_write_object_data("catalog_categories", self.client.get_catalog_categories)

    def get_campaigns(self, fetch_recipients: bool = True) -> None:
        self._initialize_result_writer("campaign")
        self._initialize_result_writer("campaign_list")
        self._initialize_result_writer("campaign_excluded_list")

        if fetch_recipients:
            self._initialize_result_writer("campaign_recipient")

        for page in self.client.get_campaigns():
            campaign_ids = [item["id"] for item in page]
            if fetch_recipients:
                self.get_campaign_recipients(campaign_ids, self._get_result_writer("campaign_recipient"))
            for item in page:
                campaign_lists = item.pop("lists")
                for campaign_list in campaign_lists:
                    self._get_result_writer("campaign_list").writerow({"campaign_id": item["id"], **campaign_list})

                excluded_lists = item.pop("excluded_lists")
                for excluded_list in excluded_lists:
                    self._get_result_writer("campaign_excluded_list").writerow(
                        {"campaign_id": item["id"], **excluded_list})

                self._get_result_writer("campaign").writerow(item)

    def get_campaign_recipients(self, campaign_ids: List[str], recipients_writer: ElasticDictWriter) -> None:
        for campaign_id in campaign_ids:
            for page in self.client.get_campaign_recipients(campaign_id):
                for item in page:
                    recipients_writer.writerow({"campaign_id": campaign_id, **item})

    def get_events(self) -> None:
        params = self.configuration.parameters
        event_settings = params.get(KEY_EVENTS_SETTINGS)

        from_timestamp = self._parse_date(event_settings.get(KEY_DATE_FROM))
        to_timestamp = self._parse_date(event_settings.get(KEY_DATE_TO))
        self.fetch_and_write_object_data("event", self.client.get_events, from_timestamp_value=from_timestamp,
                                         to_timestamp_value=to_timestamp)

    def get_profiles(self) -> None:
        params = self.configuration.parameters
        profile_settings = params.get(KEY_PROFILES_SETTINGS)
        fetch_profiles_mode = profile_settings.get(KEY_PROFILES_SETTINGS_FETCH_PROFILES_MODE)
        if fetch_profiles_mode == "fetch_all":
            self.fetch_and_write_object_data("profile", self.client.get_profiles)
        elif fetch_profiles_mode == "fetch_by_segment":
            segments = comma_separated_values_to_list(profile_settings.get(KEY_PROFILES_SETTINGS_FETCH_BY_SEGMENT, ""))
            for segment_id in segments:
                self.fetch_and_write_object_data("profile", self.client.get_segment_profiles, segment_id=segment_id)
        elif fetch_profiles_mode == "fetch_by_list":
            lists = comma_separated_values_to_list(profile_settings.get(KEY_PROFILES_SETTINGS_FETCH_BY_LIST, ""))
            for list_id in lists:
                self.fetch_and_write_object_data("profile", self.client.get_list_profiles, list_id=list_id)

    def get_flows(self) -> None:
        logging.info("The Flow endpoint does not function with the API. It will be implemented in the future")

    def get_templates(self) -> None:
        logging.info("The Templates endpoint does not function with the API. It will be implemented in the future")

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
            writer = ElasticDictWriter(table_definition.full_path, table_definition.columns)
            self.result_writers[object_name] = {"table_definition": table_definition, "writer": writer}

    def _get_result_writer(self, object_name: str) -> ElasticDictWriter:
        return self.result_writers.get(object_name).get("writer")

    def _close_all_result_writers(self) -> None:
        for object_name in self.result_writers:
            writer = self._get_result_writer(object_name)
            table_definition = self.result_writers.get(object_name).get("table_definition")
            writer.close()
            self.new_state[object_name] = copy.deepcopy(writer.fieldnames)
            table_definition.columns = copy.deepcopy(writer.fieldnames)
            self.write_manifest(table_definition)


if __name__ == "__main__":
    try:
        comp = Component()
        # this triggers the run method by default and is controlled by the configuration.action parameter
        comp.execute_action()
    except UserException as exc:
        logging.exception(exc)
        exit(1)
    except Exception as exc:
        logging.exception(exc)
        exit(2)
