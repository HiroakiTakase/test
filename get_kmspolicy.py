"""
引数で指定された環境に対してkmsポリシーの取得を行う
"""
import boto3
import botocore
import os
import json
import sys
import util.sort_functions as sort_functions
import util.common_functions as common_functions
import util.constants as constants

KEY_TYPE_CUSTOMER = "CUSTOMER"


def save_kms_policy(session, origin_profile, env):
    """
    kmsポリシーを取得し、ファイル出力を行う関数
    """
    try:
        dir_path = "./{0}/{1}/kmspolicy".format(env, origin_profile)
        os.makedirs(dir_path, exist_ok=True)
        client = session.client(constants.AWS_SERVICE_KMS)
        paginator = client.get_paginator("list_keys")

        for response in paginator.paginate():
            for key in response["Keys"]:
                alias_name = None
                key_id = key["KeyId"]
                key_type = client.describe_key(KeyId=key["KeyId"])["KeyMetadata"][
                    "KeyManager"
                ]
                # カスタマー管理型のキーのみ取得(AWSマネージド型キーは取得しない)
                if key_type == KEY_TYPE_CUSTOMER:
                    # ポリシーの取得
                    policy = client.get_key_policy(KeyId=key_id, PolicyName="default")[
                        "Policy"
                    ]

                    # エイリアスの取得
                    aliases_response = client.list_aliases(KeyId=key_id)
                    filtered_aliases = filter(
                        lambda x: "TargetKeyId" in x and x["TargetKeyId"] == key_id,
                        aliases_response["Aliases"],
                    )
                    if filtered_aliases:
                        latest_alias = max(
                            filtered_aliases,
                            key=lambda x: x.get("LastUpdatedDate", 0),
                            default=None,
                        )
                        alias_name = latest_alias["AliasName"] if latest_alias else None

                    print(alias_name, key_id)
                    if alias_name:
                        # CLIで取得したエイリアスには'/'が含まれるため置換
                        alias_name = alias_name.replace("alias/", "")
                        alias_name = alias_name.replace("/", "-")
                        filename = "./{0}/{1}/kmspolicy/{2}.json".format(
                            env, origin_profile, alias_name
                        )
                    else:
                        filename = "./{0}/{1}/kmspolicy/{2}.json".format(
                            env, origin_profile, key_id
                        )

                    data = sort_functions.sort_policy(json.loads(policy))
                    data = sort_functions.sort_item_in_dict(data)
                    data = sort_functions.format_policy(data)

                    with open(filename, "w", encoding=constants.CHARACODE_UTF8) as f:
                        json.dump(data, f, indent=4)

    except botocore.exceptions.ClientError as error:
        raise error


if __name__ == "__main__":
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
            save_kms_policy(session, origin_profile, args[1])
        except botocore.exceptions.ProfileNotFound:
            common_functions.print_profile_error(profile_name)
