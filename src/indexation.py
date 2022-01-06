import re
import json

import httplib2
from oauth2client.service_account import ServiceAccountCredentials

from src.db import db_session
from src.db.models.queue import Queue


class GoogleIndexationAPI:
    def __init__(self, queue_id: int, cred_data: str, urls_list: list,
                 domain: str, method: str, prev_data: str = None):
        self.queue_id = queue_id
        self.cred_data = json.loads(cred_data)
        self.urls_list = urls_list
        self.domain = domain
        self.method = method
        self.prev_data = json.loads(prev_data) if prev_data else None

    @staticmethod
    def get_domains(urls):
        """
        Get domains from URLs
        :param urls: all urls from file
        :type urls: list
        :return _domains:
        """
        domains = set()
        for url in urls:
            domain = re.sub(r'(.*://)?([^/?]+).*', r'\1\2', url)
            domains.add(domain)
        return domains

    def single_request_index(self, url):
        api_scopes = ["https://www.googleapis.com/auth/indexing"]
        api_endpoint = "https://indexing.googleapis.com/v3/urlNotifications:publish"
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(self.cred_data, scopes=api_scopes)
        try:
            http = credentials.authorize(httplib2.Http())
            r_content = """{""" + f"'url': '{url}', 'type': '{self.method}'" + """}"""
            response, content = http.request(api_endpoint, method="POST", body=r_content)
            log = [url, self.method, response.status, content]
            return log

        except Exception as e:
            print(e, type(e))

    @staticmethod
    def parse_response(content):
        # print(f'{content=}')
        try:
            json_line = json.loads(content)
            result = [json_line['error']['message'], json_line['error']['status']]
        except Exception as e:
            result = ['API response parse error', e]
        return result

    def indexation_worker(self):
        with db_session.create_session() as session:
            queue = session.query(Queue).get(self.queue_id)
            queue.in_progress = True
            user_id = queue.user_id
            session.add(queue)
            session.commit()
        output = ([['URL', 'METHOD', 'STATUS_CODE', 'ERROR_MESSAGE', 'ERROR_STATUS']]
                  if not self.prev_data else self.prev_data[:])
        urls_list_length = len(self.urls_list)
        if urls_list_length == 0:
            return output
        for i in range(urls_list_length):
            result = self.single_request_index(self.urls_list.pop(0))
            print(user_id, result)
            if result[2] == 429:
                print()
                return [[el.strip() if isinstance(el, str) else el for el in x] for x in output], 'out-of-limit'
            log = result[0:3]
            if result[2] != 200:
                log.extend(self.parse_response(result[3]))
            output.append(log)
            with db_session.create_session() as session:
                queue = session.query(Queue).get(self.queue_id)
                queue.urls = ','.join(self.urls_list)
                queue.data = json.dumps(output)
                session.add(queue)
                session.commit()
        print()
        return output, 'OK'