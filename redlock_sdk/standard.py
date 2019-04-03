

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

class RedLockStandard(object):
    """
    Abstraction class for a Compliance Standard in RedLock
    """
    def __init__(self, api, complianceId, debug=False):
        # super(RedLockStandard, self).__init__()

        self.uuid = complianceId
        self.api = api
        self.debug = debug

        # This is stupid. I can't just get a single Compliance Standard.
        # I have to get them all, then iterate to get the attributes for this one
        all_standards = self.api.get("compliance").json()
        for s in all_standards:
            if s['id'] == complianceId:
                self.__dict__.update(s)

        self.requirements_data = None

    def __str__(self):
        """when converted to a string, become the account_id"""
        return(self.name)

    def __repr__(self):
        """Create a useful string for this class if referenced"""
        return(f"<RedLockStandard [{self.uuid}] {self.name} >")

    def update(self, name, description=None):
        '''update this standard'''
        payload = {
            "name": name
        }
        if description is not None:
            payload['description'] = description

        response = self.api.put(f"compliance/{self.uuid}", data=payload)
        return(response.text)

    def delete(self ):
        '''delete this standard'''
        raise NotImplementedError

    def list_requirements(self):
        '''returns the raw json from RedLock API'''
        response = self.api.get(f"compliance/{self.uuid}/requirement")
        self.requirements_data = response.json()
        return(self.requirements_data)

    def requirements(self):
        '''returns an array of all requirements'''
        output = []
        if self.requirements_data is None:
            requirements_data = self.list_requirements()

        for requirementData in self.requirements_data:
            requirement = RedLockStandardRequirement(self.api, requirementData, self, self.debug)
            output.append(requirement)

        return(output)

    def requirements_by_key(self, key):
        '''Return a dict of all the requirements hashed by key'''
        output = {}
        if self.requirements_data is None:
            requirements_data = self.list_requirements()

        for requirementData in self.requirements_data:
            requirement = RedLockStandardRequirement(self.api, requirementData, self, self.debug)
            output[requirementData[key]] = requirement
        return(output)



    def add_requirement(self, requirement_number, name, description=None):
        '''Add a requirement (ie top-level section) to this standard'''
        payload = {
            "name": name,
            "requirementId": requirement_number
        }
        if description is not None:
            payload['description'] = description

        try:
            response = self.api.post(f"compliance/{self.uuid}/requirement", data=payload)
        except redlock_api.RedLockAPIError as e:
            if  e.rl_error_count == 1 and e.rl_status[0]['i18nKey'] == "duplicate_name":
                logger.warning(f"Duplicate Requirement Name: '{name}'")
            else:
                raise

        # Now go find that requirement, because I don't know what uuid it was created as
        self.list_requirements() # Need to refresh the data for this instance

        all_reqs = self.requirements_by_key('requirementId') # This will map to requirement_number
        if requirement_number not in all_reqs:
            logger.error(f"Unable to find newly created Requirement: {payload}")
            return(False)
        else:
            return(all_reqs[requirement_number])


    def get_alerts(self, policy_type=None):

        querystring = {
                    "timeType": "relative",
                    "timeAmount": "1000",
                    "timeUnit": "week",
                    "detailed": False,
                    "alert.status": "open",
                    "policy.complianceStandard": self.name
                    }
        if policy_type is not None:
            querystring['policy.type'] = policy_type
        print(querystring)
        response = self.api.get(f"v2/alert", params=querystring)
        return(response.json())


class RedLockStandardRequirement(object):
    """
    Abstraction class for a Compliance Standard Requirement (ie top-level section) in RedLock
    """
    def __init__(self, api, requirementData, ComplianceStandard, debug=False):
        # super(RedLockStandard, self).__init__()
        self.api = api
        self.debug = debug
        self.standard = ComplianceStandard
        self.__dict__.update(requirementData)
        self.uuid = requirementData['id']

    def __str__(self):
        """when converted to a string, become the account_id"""
        return(f"{self.requirementId} - {self.name}")

    def __repr__(self):
        """Create a useful string for this class if referenced"""
        return(f"<RedLockStandardRequirement [{self.uuid}] {self.requirementId} - {self.name}>")

    def list_sections(self):
        '''list all the subsections for this part of the standard'''
        response = self.api.get(f"compliance/{self.uuid}/section")
        return(response.json())

    def sections(self):
        '''returns an array of all sections'''
        output = []
        sections_data = self.list_sections().json()
        for sectionData in sections_data:
            section = RedLockStandardSection(self.api, sectionData, self, self.debug)
            output.append(section)

        return(output)

    def sections_by_key(self, key):
        '''Return a dict of all the sections hashed by key'''
        output = {}
        sections_data = self.list_sections()
        for sectionData in sections_data:
            section = RedLockStandardSection(self.api, sectionData, self, self.debug)
            output[sectionData[key]] = section
        return(output)


    def add_section(self, section_number, description):
        '''Add a subsection to this high-level requirement'''
        payload = {
            "sectionId": section_number,
            "description": description
        }
        response = self.api.post(f"compliance/{self.uuid}/section", data=payload)
        return(response.text)

        # Now go find that section, because I don't know what uuid it was created as
        all_secs = self.sections_by_key('sectionId') # This will map to section_number
        if section_number not in all_secs:
            logger.error(f"Unable to find newly created Section: {payload}")
            return(False)
        else:
            return(all_secs[section_number])

    def update(self, requirement_number, name, description=None):
        '''Update this Requirement'''
        payload = {
            "name": name,
            "requirementId": requirement_number
        }
        if description is not None:
            payload['description'] = description

        response = self.api.put(f"compliance/requirement/{self.uuid}", data=payload)
        return(response.text)

    def delete(self):
        '''Delete this Requirement'''
        raise NotImplementedError

    def get_alerts(self, policy_type=None):
        querystring = {
                    "timeType": "relative",
                    "timeAmount": "1000",
                    "timeUnit": "week",
                    "detailed": False,
                    "alert.status": "open",
                    "policy.complianceStandard": self.standard.name,
                    "policy.complianceRequirement": self.name
                    }
        if policy_type is not None:
            querystring['policy.type'] = policy_type
        print(querystring)
        response = self.api.get(f"v2/alert", params=querystring)
        return(response.json())


class RedLockStandardSection(object):
    """
    Abstraction class for a Compliance Standard Section (ie sub-section of requirement) in RedLock
    """
    def __init__(self, api, sectionData, StandardRequirement, debug=False):
        # super(RedLockStandard, self).__init__()
        self.api = api
        self.debug = debug
        self.__dict__.update(sectionData)
        self.uuid = sectionData['id']
        self.requirement = StandardRequirement
        self.standard = self.requirement.standard

    def __str__(self):
        """when converted to a string, become the account_id"""
        return(f"{self.sectionId} - {self.description}")

    def __repr__(self):
        """Create a useful string for this class if referenced"""
        return(f"<RedLockStandardRequirement [{self.uuid}] {self.sectionId} - {self.description}>")

    def update(self, section_number, description):
        payload = {
            "description": description,
            "sectionId": section_number
        }
        response = self.api.put(f"compliance/requirement/section/{self.uuid}", data=payload)
        return(response.text)

    def delete(self, sectionId):
        raise NotImplementedError

    def get_alerts(self, policy_type=None):
        querystring = {
                    "timeType": "relative",
                    "timeAmount": "1000",
                    "timeUnit": "week",
                    "detailed": False,
                    "alert.status": "open",
                    "policy.complianceStandard": self.standard.name,
                    "policy.complianceRequirement": self.requirement.name,
                    "policy.complianceSection": self.sectionId
                    }
        if policy_type is not None:
            querystring['policy.type'] = policy_type
        print(querystring)
        response = self.api.get(f"v2/alert", params=querystring)
        return(response.json())


class RedLockPolicy(object):
    """
    Abstraction class for a Compliance Standard Section (ie sub-section of requirement) in RedLock
    """
    def __init__(self, api, policy_id, debug=False):
        # super(RedLockStandard, self).__init__()
        self.api = api
        self.debug = debug
        self.uuid = policy_id
        self.policyData = self.api.get(f"policy/{self.uuid}").json()
        self.__dict__.update(self.policyData)

    def __str__(self):
        """when converted to a string, become the account_id"""
        return(f"{self.name}")

    def __repr__(self):
        """Create a useful string for this class if referenced"""
        return(f"<RedLockPolicy [{self.uuid}] {self.name}>")

    def add_section(self, redlockSection):
        '''https://api.docs.redlock.io/reference#update-policy'''

        policy = copy.deepcopy(self.policyData)

        new_standard = {
                        "complianceId": redlockSection.standard.uuid,
                        "standardDescription": redlockSection.standard.description,
                        "standardName": redlockSection.standard.name,
                        "customAssigned": False,
                        "policyId": self.uuid,
                        "requirementId": redlockSection.requirement.requirementId,
                        "requirementName": redlockSection.requirement.name,
                        "sectionId": redlockSection.sectionId,
                        "sectionLabel": redlockSection.sectionId,
                        "sectionDescription": redlockSection.description,
                        "systemDefault": False
                      }
        policy['complianceMetadata'].append(new_standard)

        try:
            response = self.api.put(f"policy/{self.uuid}", data=policy)
        except redlock_api.RedLockAPIError as e:
            print(f"Error: {e}")
            print(f"Response: {e.response.text}")
            print(f"{e.response.headers}")
            print(f"{json.dumps(policy, indent=True)}")
            raise

        # Update myself if this worked
        if response.status_code == 200:
            self.policyData = policy

        # exit(1)
        return(response)


    def remove_policy_from_section(self, policyId, sectionId):
        '''https://api.docs.redlock.io/reference#update-policy'''
        raise NotImplementedError

    def get_alerts(self, policy_type=None):
        querystring = {
                    "timeType": "relative",
                    "timeAmount": "1000",
                    "timeUnit": "week",
                    "detailed": False,
                    "alert.status": "open",
                    "policy.name": self.name,
                    }
        if policy_type is not None:
            querystring['policy.type'] = policy_type
        print(querystring)
        response = self.api.get(f"v2/alert", params=querystring)
        return(response.json())


