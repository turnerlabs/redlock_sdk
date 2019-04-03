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

    filters = [('policy.type', args.policy_type)]

    if args.cloud_type:
        filters.append(('cloud.type', args.cloud_type))


    policies = rl_api.get("policy", params=filters).json()

    if args.json:
        print(json.dumps(policies, sort_keys=True, indent=2))
    else:
        for p in policies:
            print(f"\n\n{p['name']} \n\tID: {p['policyId']}\n\tType: {p['policyType']} \n\tSeverity: {p['severity']} \n\t{p['description']}\n\tRule: {json.dumps(p['rule'])}")


def do_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", help="print debugging info", action='store_true')
    parser.add_argument("--error", help="print error info only", action='store_true')
    parser.add_argument("--username", help="RedLock Username", required=True)
    parser.add_argument("--customer", help="RedLock Customer", required=True)
    parser.add_argument("--api_endpoint", help="RedLock API Endpoint to use", default="https://api2.redlock.io")
    parser.add_argument("--policy_type", help="Policy Type", default="config")
    parser.add_argument("--cloud_type", help="Cloud Type", default=False)
    parser.add_argument("--json", help="Dump Data as json", action='store_true')


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