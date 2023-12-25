import boto3
import os
import json
import sys
import botocore
import util.sort_functions as sort_functions
import util.common_functions as common_functions
import util.constants as constants


def save_vpce_policy(vpce_id, session, origin_profile, env):
    dir_path = './{0}/{1}/vpcepolicy/'.format(env, origin_profile)
    os.makedirs(dir_path, exist_ok=True)
    client = session.client(constants.AWS_SERVICE_EC2)

    response = client.describe_vpc_endpoints(VpcEndpointIds=[vpce_id])
    endpoint = response['VpcEndpoints'][0]

    for tag in endpoint['Tags']:
        if tag.get('Key') == 'Name':
            print('{}'.format(tag['Value']))
            filename = './{0}/{1}/vpcepolicy/{2}.json'.format(env, origin_profile, tag['Value'])
            data = sort_functions.sort_policy(json.loads(endpoint['PolicyDocument']))
            data = sort_functions.format_policy(data)

            with open(filename, 'w', encoding=constants.CHARACODE_UTF8) as f:
                json.dump(data, f, indent=4)


if __name__ == '__main__':
    args = sys.argv
    origin_profile_names = common_functions.get_origin_profile_names(args)

    # コマンド引数の正常性を判定
    common_functions.validate_command_arg(args, origin_profile_names)

    profile_names = common_functions.get_profile_names(args)
    for profile_name in profile_names:
        common_functions.print_profile_name(profile_name)
        origin_profile = common_functions.get_origin_profile_name(profile_name)

        try:
            session = boto3.Session(profile_name=profile_name)
            client = session.client(constants.AWS_SERVICE_EC2)
            response = client.describe_vpc_endpoints()

            for vpce in response['VpcEndpoints']:
                save_vpce_policy(vpce['VpcEndpointId'], session, origin_profile, args[1])
        except botocore.exceptions.ProfileNotFound:
            common_functions.print_profile_error(profile_name)
