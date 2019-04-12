

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
        if not hasattr(self, "name"):
            return(f"UnNamed ({self.account_id})")
        return(f"{self.name} ({self.account_id})")

    def __init__(self):
        raise NotImplementedError # Implemented by children

    def delete(self):
        raise NotImplementedError

    def get(self):
        '''Get the data from the API for this account'''
        self.cloudData = self.api.get(f"cloud/{self.cloud_type}/{self.account_id}").json()
        self.__dict__.update(self.cloudData)

    def update(self):
        '''Update this Account.  '''
        response = self.api.put(f"cloud/{self.cloud_type}/{self.uuid}", data=self.cloudData)
        return(response.text)

    def get_alerts(self, policy_type=None, status="open"):
        '''return all alerts for all time, filtered for this account'''
        querystring = {
                    "timeType": "to_now",
                    "timeUnit": "epoch",
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

    def __repr__(self):
        """Create a useful string for this class if referenced"""
        return(f"<RedLockAWSAccount [{self.account_id}] {self.name} >")

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

    def __repr__(self):
        """Create a useful string for this class if referenced"""
        return(f"<RedLockAzureAccount [{self.account_id}] {self.name} >")

class RedLockGCPAccount(RedLockCloudAccount):
    """
    Abstraction class for an GCP Project / Organizational parent
    """
    def __init__(self, api, project_id, debug=False):
        # super(RedLockStandard, self).__init__()
        self.api = api
        self.debug = debug
        self.account_id = project_id
        self.cloud_type = "gcp"
        self.get()

    def get_subaccounts(self):
        '''Get the data from the API for this account'''
        results = self.api.get(f"cloud/{self.cloud_type}/{self.account_id}/project").json()
        self.sub_accounts = {}
        for s in results:
            # print(s)
            self.sub_accounts[s['accountId']] = RedLockGCPSubAccount(self.api, s['accountId'], self.account_id)

    def __repr__(self):
        """Create a useful string for this class if referenced"""
        return(f"<RedLockGCPAccount [{self.account_id}] {self.name} >")


class RedLockGCPSubAccount(RedLockCloudAccount):
    """
    Abstraction class for an GCP Project / Organizational parent
    """
    def __init__(self, api, project_id, parent_id, debug=False):
        # super(RedLockStandard, self).__init__()
        self.api = api
        self.debug = debug
        self.account_id = project_id
        self.parent_id = parent_id
        self.cloud_type = "gcp"
        self.get()

    # need to override this for a subaccount
    def get(self):
        '''Get the data from the API for this account'''
        results = self.api.get(f"cloud/{self.cloud_type}/{self.parent_id}/project").json()
        for s in results:
            if s['accountId'] == self.account_id:
                self.cloudData = s
                # print(s)
                self.__dict__.update(self.cloudData)
                return()
        raise Exception(f"projectId {self.account_id} was not found for organization {self.parent_id}")

    def update(self):
        raise NotImplementedError # Sub Accounts can't be updated

    def delete(self):
        raise NotImplementedError # Sub Accounts can't be deleted

    def __repr__(self):
        """Create a useful string for this class if referenced"""
        return(f"<RedLockGCPSubAccount [{self.account_id}] {self.name} >")


class RedLockAccountGroup(object):
    """
    Abstraction class for a Cloud AccountGroup in RedLock
    """
    def __init__(self, api, group_name, group_id=None, debug=False):
        # super(RedLockStandard, self).__init__()
        self.api = api
        self.debug = debug

        if group_id is None:
            # We don't know the id, must find it
            group_id = self.__find_id__(group_name)
            if group_id is None:
                # Well shit, doesn't exist
                raise RedLockAccountGroupNotFoundError(group_name)

        self.group_id = group_id
        self.get()

    @classmethod
    def create(cls, rl_api, group_name, description):
        '''Classmethod to create a new account group'''
        payload = {
            "name": group_name,
            "description": description,
            "accountIds": []
        }
        response = rl_api.post("cloud/group", data=payload)

        # Now return an instantiated class
        return(cls(rl_api, group_name))

    @classmethod
    def all(cls, rl_api):
        '''Classmethod to return an hash of all RedLockAccountGroup indexed by name'''
        output = {}
        account_groups = rl_api.get("cloud/group").json()
        for g in account_groups:
            output[g['name']] = RedLockAccountGroup(rl_api, g['name'], group_id=g['id'])
        return(output)

    def __find_id__(self, group_name):
        '''Given the name (primary key) get the id (which is neede by the API)'''
        groups = self.api.get(f"cloud/group/name").json()
        for g in groups:
            if g['name'] == group_name:
                return(g['id'])
        return(None)

    def __str__(self):
        """when converted to a string, become the account_id"""
        return(f"{self.name}")

    def __repr__(self):
        """Create a useful string for this class if referenced"""
        return(f"<RedLockAccountGroup {self.name} >")

    def update(self):
        response = self.api.put(f"cloud/{self.cloud_type}/{self.uuid}", data=self.cloudData)
        return(response.text)

    def delete(self):
        raise NotImplementedError # Implemented by children

    def get(self):
        '''Get the data from the API for this account group'''

        # This call doesn't return the same data that the /cloud/group returns.
        # self.groupData = self.api.get(f"cloud/group/{self.group_id}").json()

        # Pull everything and find the one block I need
        all_groups = self.api.get(f"cloud/group/").json()
        for g in all_groups:
            if g['id'] == self.group_id:
                self.groupData = g
                self.__dict__.update(self.groupData)
                return
        raise Exception

    def update(self):
        '''Update this AccountGroup. Note: Not all of the GroupData should be set back on the update  '''

        # These are the only valid payloads
        payload = {
            "accountIds": self.accountIds,
            "description": self.description,
            "name": self.name
        }
        response = self.api.put(f"cloud/group/{self.group_id}", data=payload)
        return(response.text)

    def get_alerts(self, policy_type=None, status="open"):
        '''return alerts for the Account Group. You can filter by policy_type and status'''
        querystring = {
                    "timeType": "to_now",
                    "timeUnit": "epoch",
                    "detailed": False,
                    "alert.status": status,
                    "account.group": self.name
                    }

        if policy_type is not None:
            querystring['policy.type'] = policy_type

        print(querystring)
        response = self.api.get(f"v2/alert", params=querystring)
        return(response.json())

    def get_account_ids_by_cloud_type(self, cloud_type):
        output = []
        for a in self.accounts:
            if a['type'] == cloud_type:
                output.append(a['id'])
        return(output)

    def add_account(self, cloud_account):
        '''add an account to this account group'''
        self.accountIds.append(cloud_account.account_id)
        self.update() and self.get()

    def remove_account(self, cloud_account):
        '''remove an account from this account group'''
        self.accountIds.remove(cloud_account.account_id)
        self.update() and self.get()

    def get_accounts(self, cloud_type=None):
        '''Return array of CloudAccount objects'''
        output=[]
        for a in self.accounts:

            if a['type'] == "gcp" and (cloud_type is None or cloud_type == "gcp"):
                output.append(RedLockGCPAccount(self.api, a['id']))
            elif a['type'] == "aws" and (cloud_type is None or cloud_type == "aws"):
                output.append(RedLockAWSAccount(self.api, a['id']))
            elif a['type'] == "azure" and (cloud_type is None or cloud_type == "azure"):
                output.append(RedLockAzureAccount(self.api, a['id']))
        return(output)





