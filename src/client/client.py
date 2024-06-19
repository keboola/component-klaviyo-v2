import json
import logging
from typing import Iterator, Callable, Dict, List, Tuple

from klaviyo_api import KlaviyoAPI
from openapi_client.exceptions import OpenApiException

MAX_DELAY = 60
MAX_RETRIES = 5


class KlaviyoClientException(Exception):
    pass


class KlaviyoClient:
    def __init__(self, api_token: str):
        self.client = KlaviyoAPI(api_token, max_delay=MAX_DELAY, max_retries=MAX_RETRIES)

    def get_metrics(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Metrics.get_metrics)

    def get_catalog_items(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Catalogs.get_catalog_items)

    def get_catalog_categories(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Catalogs.get_catalog_categories)

    def get_events(self, from_timestamp_value: int, to_timestamp_value: int) -> Iterator[List[Dict]]:
        request_filter = f"greater-or-equal(timestamp,{from_timestamp_value})," \
                         f"less-or-equal(timestamp,{to_timestamp_value})"
        return self._paginate_cursor_endpoint(self.client.Events.get_events, filter=request_filter)

    def get_lists(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Lists.get_lists)

    def get_list(self, list_id: str) -> Dict:
        try:
            return self.client.Lists.get_list(list_id)
        except OpenApiException as api_exc:
            error_message = self._process_error(api_exc)
            raise KlaviyoClientException(error_message) from api_exc

    def get_list_ids(self) -> List[Dict]:
        all_list_ids = []
        for page in self._paginate_cursor_endpoint(self.client.Lists.get_lists):
            all_list_ids.extend({"id": row.get("id"), "name": row.get("attributes").get("name")} for row in page)
        return all_list_ids

    def get_segment_ids(self) -> List[Dict]:
        all_segment_ids = []
        for page in self._paginate_cursor_endpoint(self.client.Segments.get_segments):
            all_segment_ids.extend({"id": row.get("id"), "name": row.get("attributes").get("name")} for row in page)
        return all_segment_ids

    def get_list_profiles(self, list_id: str) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Lists.get_list_profiles, list_id=list_id)

    def get_profiles(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Profiles.get_profiles)

    def get_segments(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Segments.get_segments)

    def get_segment(self, segment_id):
        try:
            return self.client.Segments.get_segment(segment_id)
        except OpenApiException as api_exc:
            error_message = self._process_error(api_exc)
            raise KlaviyoClientException(error_message) from api_exc

    def get_segment_profiles(self, segment_id: str) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Segments.get_segment_profiles, id=segment_id)

    def get_flows(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Flows.get_flows)

    def get_templates(self) -> Iterator[List[Dict]]:
        return self._paginate_cursor_endpoint(self.client.Templates.get_templates)

    def get_campaigns(self, channel: str) -> Iterator[List[Dict]]:
        campaigns = self.client.Campaigns.get_campaigns(filter=f"equals(messages.channel,'{channel}')")
        for r in campaigns.get("data"):
            yield r

    def _paginate_cursor_endpoint(self, endpoint_func: Callable, **kwargs) -> Iterator[List[Dict]]:
        try:
            current_page = endpoint_func(**kwargs)
        except OpenApiException as api_exc:
            error_message = self._process_error(api_exc)
            raise KlaviyoClientException(error_message) from api_exc
        yield current_page.get("data")

        while next_page := current_page.get("links").get("next"):
            try:
                current_page = endpoint_func(**kwargs, page_cursor=next_page)
            except OpenApiException as api_exc:
                error_message = self._process_error(api_exc)
                raise KlaviyoClientException(error_message) from api_exc
            yield current_page.get("data")

    def _process_error(self, api_exc: Exception) -> str:
        try:
            error_data = json.loads(api_exc.body)
        except json.JSONDecodeError as exc:
            raise KlaviyoClientException(f"Error Occurred. Failed to decode error : {api_exc.body}") from exc
        if len(error_data.get('errors', [])) == 0:
            return error_data
        error = error_data.get('errors')[0]
        return self._generate_error_message_v2_client(error)

    @staticmethod
    def _generate_error_message_v2_client(error_data: Dict) -> str:
        error_detail = f"{error_data.get('title')} {error_data.get('detail')}"
        if error_data.get('status') == 401:
            error_name = f"Not Authorized Error ({error_data.get('status')})"
        elif error_data.get('status') == 403:
            error_name = f"Forbidden Error ({error_data.get('status')})"
        elif error_data.get('status') == 404:
            error_name = f"Not Found Error ({error_data.get('status')})"
        else:
            error_name = f"{error_data.get('code')} ({error_data.get('status')})"
        return f"{error_name} : {error_detail}"

    def test_credentials(self) -> Tuple[bool, Dict, Exception]:
        """
        Test credentials. Returns list of unauthorized scopes if present,

        Returns:

        """
        missing_scopes = dict()
        valid_token = False
        last_exception = None
        test_scopes = {"campaigns": self.client.Campaigns.get_campaigns,
                       "catalogs": self.client.Catalogs.get_catalog_items,
                       "events": self.client.Events.get_events,
                       "lists": self.client.Lists.get_lists,
                       "metrics": self.client.Metrics.get_metrics,
                       "profiles": self.client.Profiles.get_profiles,
                       "segments": self.client.Segments.get_segments
                       }

        # test scopes
        for scope in test_scopes:
            try:
                if scope == "campaigns":
                    test_scopes[scope](filter=f"equals(messages.channel,'email')")
                else:
                    test_scopes[scope]()

                valid_token = True
            except OpenApiException as e:
                json_resp = json.loads(e.body)
                detail = ''
                reason = e.reason
                if json_resp.get('errors'):
                    detail = json_resp['errors'][0]["detail"]

                logging.debug(f"Test {scope} scope failed with {e}")
                missing_scopes[scope] = f'{reason}: {detail}'
                # token is valid when unauthorized error received
                if e.status == 403:
                    valid_token = True
                else:
                    last_exception = e

        return valid_token, missing_scopes, last_exception
