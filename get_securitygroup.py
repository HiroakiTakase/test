"""
引数で指定された環境に対してセキュリティグループの取得を行う
"""
import boto3
import botocore
import os
import json
import sys
import util.sort_functions as sort_functions
import util.common_functions as common_functions
import util.constants as constants

KEY_SECURITY_GROUPS = "SecurityGroups"
KEY_GROUP_NAME = "GroupName"
DIR_NAME_SECURITYGROUP = "securitygroup"
GROUP_NAME_DAFAULT = [
    "default",
    "ElasticMapReduce-master",
    "ElasticMapReduce-Master-Private",
    "ElasticMapReduce-ServiceAccess",
    "ElasticMapReduce-slave",
    "ElasticMapReduce-Slave-Private",
]
KEYS_TO_REMOVE = ["PeeringStatus", "VpcId", "VpcPeeringConnectionId"]


def split_sgrules(rules):
    """
    セキュリティグループ内のルールをマネコンの表記にあうよう分割する関数
    """
    keys = ["IpRanges", "Ipv6Ranges", "PrefixListIds", "UserIdGroupPairs"]
    new_rules = []
    for rule in rules:
        common = {k: v for k, v in rule.items() if k not in keys}
        for key in keys:
            for sub_item in rule.get(key, []):
                new_rule = common.copy()
                new_rule.update(sub_item)
                new_rules.append(new_rule)
    return new_rules


def format_securitygroup(sg_dict):
    """
    セキュリティグループの出力形式を整形する関数
    """
    # キー名の置換マップを定義
    rename_map = {
        "IpPermissions": "InboundRules",
        "IpPermissionsEgress": "OutboundRules",
    }
    # 項目の配置順を定義
    orderl1 = [
        "GroupName",
        "GroupId",
        "Description",
        "VpcId",
        "OwnerId",
        "InboundRules",
        "OutboundRules",
        "Tags",
    ]
    orderl2 = [
        "FromPort",
        "ToPort",
        "IpProtocol",
        "CidrIp",
        "CidrIpv6",
        "PrefixListId",
        "GroupId",
        "UserId",
        "Description",
    ]

    # キー名の置換
    sg_dict = {rename_map.get(key, key): sg_dict[key] for key in sg_dict.keys()}

    # 第一階層のソート
    sorted_dict = {key: sg_dict[key] for key in orderl1 if key in sg_dict}

    # インバウンドおよびアウトバウンドのルールをマネコンの表記にあうよう分割
    for rule in ["InboundRules", "OutboundRules"]:
        if rule in sorted_dict:
            sorted_dict[rule] = split_sgrules(sorted_dict[rule])

    # インバウンドおよびアウトバウンドルール内のソート
    for rule in ["InboundRules", "OutboundRules"]:
        if rule in sorted_dict:
            for item in sorted_dict[rule]:
                # 表記を統一するために不足している要素を追加
                for key in orderl2:
                    if key not in item:
                        item[key] = ""
                    # FromPort,ToPortが数値の場合、文字列に変換
                    elif key in ["FromPort", "ToPort"] and isinstance(item[key], int):
                        item[key] = str(item[key])

            sorted_dict[rule] = [
                dict(sorted(item.items(), key=lambda x: orderl2.index(x[0])))
                for item in sorted_dict[rule]
            ]

    return sorted_dict


def save_security_group(group_name, data, origin_profile, env):
    """
    セキュリティグループポリシーをファイル出力する関数
    """
    dir_path = "./{0}/{1}/{2}/".format(env, origin_profile, DIR_NAME_SECURITYGROUP)
    os.makedirs(dir_path, exist_ok=True)
    filename = "./{0}/{1}/{2}/{3}.json".format(
        env, origin_profile, DIR_NAME_SECURITYGROUP, group_name
    )
    print("{}".format(group_name))

    # ソート用キーを追加
    data = sort_functions.add_key(
        data, constants.SORT_INFO_IN_SGRULE, constants.MERGED_KEY
    )
    # キーリストに基づいてソート
    data = sort_functions.sort_dict_in_list(data, constants.MERGED_KEY)
    # ソート用キーの削除
    data = sort_functions.remove_key(data, constants.MERGED_KEY)

    # Tags内をソート
    data = sort_functions.sort_dict_in_list(data, "Key")

    with open(filename, "w", encoding=constants.CHARACODE_UTF8) as f:
        json.dump(data, f, indent=4)


if __name__ == "__main__":
    args = sys.argv
    origin_profile_names = common_functions.get_origin_profile_names(args)

    # コマンド引数の正常性を判定
    common_functions.validate_command_arg(args, origin_profile_names)

    sgid_path = "./list/{0}_vpcid.txt".format(args[1])

    # VPCマッピングファイルを読み込み、処理に合わせた形で辞書に代入
    vpc_id_mapping = {}
    with open(sgid_path, "r", encoding=constants.CHARACODE_UTF8) as securityid_file:
        for line in securityid_file:
            values = line.strip().split(",")
            key = values[1]
            value = values[0]
            vpc_id_mapping[key] = value

    profile_names = common_functions.get_profile_names(args)
    for profile_name in profile_names:
        common_functions.print_profile_name(profile_name)
        origin_profile = common_functions.get_origin_profile_name(profile_name)

        try:
            session = boto3.Session(profile_name=profile_name)
            client = session.client(constants.AWS_SERVICE_EC2)
            response = client.describe_security_groups()

            # セキュリティグループの取得
            for security_group in response[KEY_SECURITY_GROUPS]:
                group_name = security_group[KEY_GROUP_NAME]
                # セキュリティグループの名前がデフォルト値の場合、VPC名を先頭に付与する
                if security_group[KEY_GROUP_NAME] in GROUP_NAME_DAFAULT:
                    vpc_name = vpc_id_mapping[security_group["VpcId"]]
                    group_name = "{0}-{1}".format(
                        vpc_name, security_group[KEY_GROUP_NAME]
                    )

                # GUIに表示されないルール内の情報を削除
                for ip_permission in security_group.get("IpPermissions", []):
                    for user_id_group_pair in ip_permission.get("UserIdGroupPairs", []):
                        for key_to_remove in KEYS_TO_REMOVE:
                            if key_to_remove in user_id_group_pair:
                                del user_id_group_pair[key_to_remove]
                for ip_permission in security_group.get("IpPermissionsEgress", []):
                    for user_id_group_pair in ip_permission.get("UserIdGroupPairs", []):
                        for key_to_remove in KEYS_TO_REMOVE:
                            if key_to_remove in user_id_group_pair:
                                del user_id_group_pair[key_to_remove]

                # 取得した情報のフォーマットを整形
                security_group = format_securitygroup(security_group)

                save_security_group(group_name, security_group, origin_profile, args[1])
        except botocore.exceptions.ProfileNotFound:
            common_functions.print_profile_error(profile_name)
