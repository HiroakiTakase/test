import os
from collections import OrderedDict

KEY_STATEMENT = "Statement"
KEY_IN_SECURITYGROUP = ["IpPermissions", "IpPermissionsEgress"]
TARGET_DICT_NAMES = [
    "StringEquals",
    "StringNotEquals",
    "StringLike",
    "StringNotLike",
    "ArnEquals",
    "ArnNotEquals",
    "ArnLike",
    "ArnNotLike",
    "Principal",
]
POLICY_ORDER_L1 = ["Version", "Id", "Statement"]
POLICY_ORDER_L2 = [
    "Sid",
    "Effect",
    "Principal",
    "NotPrincipal",
    "Action",
    "NotAction",
    "Resource",
    "NotResource",
    "Condition",
    "NotCondition",
]


def sort_all_list_in_dict(target_dict):
    for key, value in target_dict.items():
        if isinstance(value, list):
            target_dict[key] = sorted(value)
        elif isinstance(value, dict):
            sort_all_list_in_dict(value)
    return target_dict


def sort_policy(policy_dict):
    if not isinstance(policy_dict[KEY_STATEMENT], list):
        policy_dict[KEY_STATEMENT] = sort_all_list_in_dict(policy_dict[KEY_STATEMENT])
        return policy_dict
    i = 0
    for statement in policy_dict[KEY_STATEMENT]:
        policy_dict[KEY_STATEMENT][i] = sort_all_list_in_dict(statement)
        i += 1
    return policy_dict


def sort_item_in_specified_dict(policy_dict, target_name):
    """
    特定の辞書内のアイテムをソートする関数
    """
    for key, value in policy_dict.items():
        if key == target_name and isinstance(value, dict):
            policy_dict[key] = dict(sorted(value.items(), key=lambda item: item[0]))
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                if isinstance(item, dict):
                    policy_dict[key][idx] = sort_item_in_specified_dict(
                        item, target_name
                    )
        elif isinstance(value, dict):
            policy_dict[key] = sort_item_in_specified_dict(value, target_name)
    return policy_dict


def sort_item_in_dict(policy_dict):
    """
    辞書内のアイテムをソートする関数
    """
    for target in TARGET_DICT_NAMES:
        sort_item_in_specified_dict(policy_dict, target)
    return policy_dict


def sort_dict_in_list(policy_dict, sort_key):
    """
    リスト内の辞書をソートする関数
    """
    if isinstance(policy_dict, list):
        if (
            policy_dict
            and isinstance(policy_dict[0], dict)
            and sort_key in policy_dict[0]
        ):
            policy_dict.sort(key=lambda x: x[sort_key])
    elif isinstance(policy_dict, dict):
        for key in policy_dict:
            sort_dict_in_list(policy_dict[key], sort_key)
    return policy_dict


def add_key(target_dict, keys_to_join, combined_key_name):
    """
    辞書に新しいキーを追加する関数
    """
    if all(key in target_dict for key in keys_to_join):
        target_dict[combined_key_name] = "_".join(
            [target_dict[key] for key in keys_to_join]
        )
    else:
        for sub_data in target_dict.values():
            if isinstance(sub_data, dict):
                add_key(sub_data, keys_to_join, combined_key_name)
            elif isinstance(sub_data, list):
                for item in sub_data:
                    if isinstance(item, dict):
                        add_key(item, keys_to_join, combined_key_name)

    return target_dict


def remove_key(target_dict, key_to_remove):
    """
    辞書内の指定のキーを削除する関数
    """
    for key in list(target_dict.keys()):
        if key == key_to_remove:
            del target_dict[key]
        elif isinstance(target_dict[key], dict):
            remove_key(target_dict[key], key_to_remove)
        elif isinstance(target_dict[key], list):
            for item in target_dict[key]:
                if isinstance(item, dict):
                    remove_key(item, key_to_remove)
    return target_dict


def format_policy(target_dict):
    """
    ポリシーの出力順序を整形する関数
    """
    # 第一階層の表示順の制御
    sorted_dict = {
        key: target_dict[key] for key in POLICY_ORDER_L1 if key in target_dict
    }

    # Statement内の表示順の制御
    if isinstance(sorted_dict["Statement"], list):
        for index in range(len(sorted_dict["Statement"])):
            temp_dict = OrderedDict()

            for key in POLICY_ORDER_L2:
                if key in sorted_dict["Statement"][index]:
                    temp_dict[key] = sorted_dict["Statement"][index][key]
            sorted_dict["Statement"][index] = temp_dict

    return sorted_dict
