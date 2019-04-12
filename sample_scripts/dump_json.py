#!/usr/bin/env python3


import json
import sys
import getpass
import datetime
from dateutil import tz
import time

from pprint import pprint

try:
    from redlock_sdk import *
except ImportError as e:
    print("must install redlock sdk")
    print("Error: {}".format(e))
    exit(1)


import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Quiet Boto3
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('keyring').setLevel(logging.WARNING)


def main(args):

    rl_api = redlock_api.RedLockAPI(args.api_endpoint, debug=args.debug, customerName=args.customer)
    if not rl_api.authenticate(args.username):
        print("Login Failed")
        exit(1)


    # Dump Cloud Accounts
    filename = "cloud_accounts.json"
    data = rl_api.get("cloud")
    file = open(f"{args.path}/{filename}","w")
    file.write(json.dumps(data.json(), sort_keys=True, indent=2))
    file.close()

    # Dump Cloud Account groups
    filename = "cloud_account_groups.json"
    data = rl_api.get("cloud/group")
    file = open(f"{args.path}/{filename}","w")
    file.write(json.dumps(data.json(), sort_keys=True, indent=2))
    file.close()

    # Dump policies
    filename = "policies.json"
    data = rl_api.get("policy")
    file = open(f"{args.path}/{filename}","w")
    file.write(json.dumps(data.json(), sort_keys=True, indent=2))
    file.close()

    # Dump policies
    filename = "policy_compliance_standards.json"
    data = rl_api.get("policy/compliance")
    file = open(f"{args.path}/{filename}","w")
    file.write(json.dumps(data.json(), sort_keys=True, indent=2))
    file.close()

    filename = "standards.json"
    data = rl_api.get("compliance")
    file = open(f"{args.path}/{filename}","w")
    file.write(json.dumps(data.json(), sort_keys=True, indent=2))
    file.close()


    filename = "reports.json"
    data = rl_api.get("report")
    file = open(f"{args.path}/{filename}","w")
    file.write(json.dumps(data.json(), sort_keys=True, indent=2))
    file.close()

    # These next two require the standardId and RequirementId, so I can just dump them.
    # filename = "requirements.json"
    # data = rl_api.get(f"compliance/{complianceId}/requirement")
    # file = open(f"{args.path}/{filename}","w")
    # file.write(json.dumps(data.json(), sort_keys=True, indent=2))
    # file.close()

    # filename = "sections.json"
    # data = rl_api.get(f"compliance/{requirementId}/section")
    # file = open(f"{args.path}/{filename}","w")
    # file.write(json.dumps(data.json(), sort_keys=True, indent=2))
    # file.close()



    # Get alerts. There can be a lot of these!
    filename = "alerts.json"
    querystring = {
            "timeType": "to_now",
            "timeUnit": "epoch",
            "detailed": False
            }
    data = rl_api.get("v2/alert", params=querystring)
    file = open(f"{args.path}/{filename}","w")
    file.write(json.dumps(data.json(), sort_keys=True, indent=2))
    file.close()

    # Filtering Options. These have some pre-populated "suggestions" specific to your RedLock Tenant.
    filename = "filters.json"
    data = rl_api.get("filter/alert/suggest")
    file = open(f"{args.path}/{filename}","w")
    file.write(json.dumps(data.json(), sort_keys=True, indent=2))
    file.close()

def do_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", help="print debugging info", action='store_true')
    parser.add_argument("--error", help="print error info only", action='store_true')
    parser.add_argument("--username", help="RedLock Username", required=True)
    parser.add_argument("--customer", help="RedLock Customer", required=True)
    parser.add_argument("--api_endpoint", help="RedLock API Endpoint to use", default="https://api2.redlock.io")
    parser.add_argument("--path", help="Dump Data to this path", default="json_dumps")


    args = parser.parse_args()

    # Logging idea stolen from: https://docs.python.org/3/howto/logging.html#configuring-logging
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    if args.debug:
        ch.setLevel(logging.DEBUG)
    elif args.error:
        ch.setLevel(logging.ERROR)
    else:
        ch.setLevel(logging.INFO)
    # create formatter
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)

    return(args)


if __name__ == '__main__':
    args = do_args()
    main(args)