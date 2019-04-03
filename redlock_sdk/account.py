

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


class RedLockCloudAccount(object):
    """
    Abstraction class for a Cloud Account in RedLock
    """

    def __str__(self):
        """when converted to a string, become the account_id"""
        return(f"{self.name} ({self.account_id})")

    def __repr__(self):
        """Create a useful string for this class if referenced"""
        return(f"<RedLockCloudAccount [{self.account_id}] {self.name} >")

    def __init__(self):
        raise NotImplementedError # Implemented by children

    def update(self):
        raise NotImplementedError # Implemented by children

    def delete(self):
        raise NotImplementedError # Implemented by children

    def get(self):
        '''Get the data from the API for this account'''
        self.cloudData = self.api.get(f"cloud/{self.cloud_type}/{self.account_id}").json()
        self.__dict__.update(self.cloudData)

    def update(self):
        '''Update this Account.  '''
        response = self.api.put(f"cloud/{self.cloud_type}/{self.uuid}", data=self.cloudData)
        return(response.text)

    def get_alerts(self, policy_type=None, status="open"):

        querystring = {
                    "timeType": "relative",
                    "timeAmount": "1000",
                    "timeUnit": "week",
                    "detailed": False,
                    "alert.status": status,
                    "cloud.accountId": self.account_id,
                    "cloud.type": self.cloud_type
                    # "cloud.account": self.name
                    }

        if policy_type is not None:
            querystring['policy.type'] = policy_type

        print(querystring)
        response = self.api.get(f"v2/alert", params=querystring)
        return(response.json())

    def dismiss_alert(self, alert_id, dismissal_message):
        '''Validate alert_id applies to this account, and dismiss it'''
        raise NotImplementedError





class RedLockAWSAccount(RedLockCloudAccount):
    """
    Abstraction class for a AWS Account
    self.cloudData is defined here: https://api.docs.redlock.io/reference#add-aws-account
    """
    def __init__(self, api, account_id, debug=False):
        # super(RedLockStandard, self).__init__()
        self.api = api
        self.debug = debug
        self.account_id = account_id
        self.cloud_type = "aws"
        self.get()


class RedLockAzureAccount(RedLockCloudAccount):
    """
    Abstraction class for an Azure Account
    """
    def __init__(self, api, subscription_id, debug=False):
        # super(RedLockStandard, self).__init__()
        self.api = api
        self.debug = debug
        self.account_id = subscription_id
        self.cloud_type = "azure"
        self.get()

class RedLockGCPAccount(RedLockCloudAccount):
    """
    Abstraction class for an Azure Account
    """
    def __init__(self, api, project_id, debug=False):
        # super(RedLockStandard, self).__init__()
        self.api = api
        self.debug = debug
        self.account_id = project_id
        self.cloud_type = "azure"
        self.get()




