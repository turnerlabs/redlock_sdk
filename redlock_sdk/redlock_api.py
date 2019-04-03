

# from botocore.exceptions import ClientError, ConnectionError
# import boto3

import json
import sys
import getpass
import datetime
from dateutil import tz
import copy
import requests

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import logging
logger = logging.getLogger()


cafile = requests.certs.where()
# print("cafile: {}".format(cafile))

class RedLockAPI(object):
    """
    Defines a generic Redlock API. This class should not be used directly

    General idea taken from https://github.com/ebeuerle/compliance_report_email/blob/master/lib/redlock_sdk.py

    """

    # Max number of retries for any reason
    max_retries = 5
    # Always retry on these statuses, within the requests session.
    # We retry for auth failure (401) within the SDK code. See try_wrapper().
    retry_statuses = [429, 500, 502, 503, 504]

    def __init__(self, endpoint, customerName=None, debug=False):
        super(RedLockAPI, self).__init__()


        self.debug = debug
        if self.debug:
            self.max_retries = 1
            logger.setLevel(logging.DEBUG)

        self.endpoint = endpoint
        self.customerName = customerName
        self.header = None # Set to none and reset after authenticating

        self.client = requests.Session()
        self.retries = Retry(total=self.max_retries,
                                 status_forcelist=self.retry_statuses,
                                 backoff_factor=1)
        self.redlock_http_adapter = HTTPAdapter(pool_connections=1,
                                                    pool_maxsize=10)
                                                    # max_retries=self.retries)
        self.session_mount = "https://"
        self.client.mount(self.session_mount, self.redlock_http_adapter)




    def __get_password__(self, username):
        '''gets the password from the keychain or prompts if not available'''
        keyring_user = username.replace('\\', '-')
        try:
            import keyring
            password = keyring.get_password('redlock', keyring_user)
            HAS_KEYRING=True
        except:
            HAS_KEYRING=False
            password = None
        if not password:
            password = getpass.getpass()
            if HAS_KEYRING:
                keyring.set_password('redlock', keyring_user, password)
        return password

    def authenticate(self, username, pw=None):
        '''Authenticate to RedLock and get a token'''
        try:
            if pw:
                password = pw
            else:
                password = self.__get_password__(username)

            url = "{}/login".format(self.endpoint)
            if self.customerName is not None:
                body = {"username":username,"password":password,"customerName":self.customerName} # FIXME to support customerName
            else:
                body = {"username":username,"password":password}

            resp = self.client.post(url, json=body)
            if resp.status_code == 200:
                auth_resp_json = resp.json()
                token = auth_resp_json["token"]
                self.auth_token = token
                self.username = username
                self.header = {"x-redlock-auth": self.auth_token,"Content-Type": "application/json"}
                self.client.headers.update(self.header)
                return True
            else:
                logger.error(f"Failed to authenticate as {username} to {url}: {resp}")
                return False
        except Exception as e:
            logger.error("Exception Authenticating to RedLock: {}".format(e))
            return False


    def get(self, path, params=None):
        '''Executes a GET operation against the API for the path specificed'''

        if self.header is None:
            raise RedLockAPIUnauthenticated(f"Cannot get {path}: Not Authenticated")

        url = f"{self.endpoint}/{path}"

        if self.debug:
            logger.debug(f"Getting {url} with params {params}")

        response = self.client.get(url, params=params)

        if self.debug:
            logger.debug(f"Response: {response.text}")

        if response.status_code == 200:
            return(response)
        else:
            raise RedLockAPIError(response)


    def put(self, path, data=None):
        '''Executes a PUT operation against the API for the path specificed'''

        if self.header is None:
            raise RedLockAPIUnauthenticated(f"Cannot get {path}: Not Authenticated")

        url = f"{self.endpoint}/{path}"

        if self.debug:
            logger.debug(f"Putting {url} with data {data}")

        response = self.client.put(url, data=json.dumps(data))
        if response.status_code == 200:
            return(response)
        else:
            raise RedLockAPIError(response)



    def post(self, path, data=None):
        '''Executes a POST operation against the API for the path specificed'''

        if self.header is None:
            raise RedLockAPIUnauthenticated(f"Cannot get {path}: Not Authenticated")

        url = f"{self.endpoint}/{path}"

        if self.debug:
            logger.debug(f"Posting {url} with data {data}")

        response = self.client.post(url, data=json.dumps(data))
        if self.debug:
            logger.debug(f"Headers: {response.headers}")
            logger.debug(f"Body: {response.text}")

        if response.status_code == 200:
            return(response)
        else:
            raise RedLockAPIError(response)



class RedLockAPIError(Exception):
    '''raised when the RedLock API fails to process a request'''
    def __init__(self, response):
        self.message = f"{response.status_code} - {response.reason}: {response.headers['x-redlock-status']}"
        self.status_code = response.status_code
        self.reason = response.reason
        self.response = response
        self.rl_status = json.loads(response.headers['x-redlock-status'])
        self.rl_error_count = len(self.rl_status)
        super().__init__(self.message)



class RedLockAPIUnauthenticated(Exception):
    '''raised when the RedLock API fails to process a request'''

