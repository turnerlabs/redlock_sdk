

# from botocore.exceptions import ClientError, ConnectionError
# import boto3

import json
import sys
import getpass
import datetime
from dateutil import tz
import copy

import logging
logger = logging.getLogger()

try:
    from redlock_sdk import *
except ImportError as e:
    print("must install redlock sdk")
    print("Error: {}".format(e))
    exit(1)


class RedLockReport(object):
    """
    Abstraction class for a Cloud AccountGroup in RedLock
    """

    def __init__(self, api, report_name, report_id=None, debug=False):
        self.api = api
        self.debug = debug

        if report_id is None:
            # We don't know the id, must find it
            report_id = self.__find_id__(report_name)
            if report_id is None:
                # Well shit, doesn't exist
                raise RedLockAccountReportNotFoundError(report_name)

        self.report_id = report_id
        self.get()


    # @classmethod
    # def create(cls, rl_api, group_name, description):
    #     '''Classmethod to create a new account group'''
    #     payload = {
    #         "name": group_name,
    #         "description": description,
    #         "accountIds": []
    #     }
    #     response = rl_api.post("cloud/group", data=payload)

    #     # Now return an instantiated class
    #     return(cls(rl_api, group_name))


    def __find_id__(self, report_name):
        '''Given the name (primary key) get the id (which is neede by the API)'''
        reports = self.api.get(f"report").json()
        for r in reports:
            if r['name'] == report_name:
                return(r['id'])
        return(None)


    def __str__(self):
        """when converted to a string, become the account_id"""
        return(f"{self.name}")

    def __repr__(self):
        """Create a useful string for this class if referenced"""
        return(f"<RedLockReport {self.name} >")

    def update(self):
        raise NotImplementedError
        response = self.api.put(f"report/{self.report_id}", data=self.reportData)
        self.get() # Refresh myself

    def delete(self):
        raise NotImplementedError

    def get(self):
        '''Get the data from the API for this account group'''
        self.reportData = self.api.get(f"report/{self.report_id}").json()
        self.__dict__.update(self.reportData)

    def download(self, filename):
        r = self.api.get(f"report/{self.report_id}/download")
        if r.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)


    def add_account(self, cloud_account):
        '''add an account to this account group'''
        raise NotImplementedError
        self.reportData['target']['accounts'].append(cloud_account.account_id)
        self.update() and self.get()

    def remove_account(self, cloud_account):
        '''remove an account from this account group'''
        raise NotImplementedError
        self.reportData['target']['accounts'].remove(cloud_account.account_id)
        self.update() and self.get()

