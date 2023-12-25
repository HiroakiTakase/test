import boto3
import botocore
import os
import json
import sys
import util.sort_functions as sort_functions
import util.common_functions as common_functions
import util.constants as constants


def save_bucket_policy(bucket_name, session, origin_profile, env):
    """
    対象環境のフォルダと取得したバケットポリシーファイルの作成
    """
    try:
        print(bucket_name)

        dir_path = './{0}/{1}/bucketpolicy/'.format(env, origin_profile)
        os.makedirs(dir_path, exist_ok=True)
        client = session.client(constants.AWS_SERVICE_S3)

        response = client.get_bucket_policy(Bucket=bucket_name)

        # ファイル内容のソート
        data = sort_functions.sort_policy(json.loads(response['Policy']))
        data = sort_functions.sort_item_in_dict(data)
        data = sort_functions.format_policy(data)
        filename = './{0}/{1}/bucketpolicy/{2}.json'.format(env, origin_profile, bucket_name)

        with open(filename, 'w', encoding=constants.CHARACODE_UTF8) as f:
            json.dump(data, f, indent=4)

    except botocore.exceptions.ClientError as error:
        print(bucket_name)
        print(error)


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
            s3_resource = session.resource(constants.AWS_SERVICE_S3)
            for bucket in s3_resource.buckets.all():
                save_bucket_policy(bucket.name, session, origin_profile, args[1])
        except botocore.exceptions.ProfileNotFound:
            common_functions.print_profile_error(profile_name)
