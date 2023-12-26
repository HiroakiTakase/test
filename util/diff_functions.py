"""
get_diff.pyにて使用する関数ファイル
"""
import difflib
import os
import csv
import sort_functions
import json
import constants


def create_folder_paths(dev_folder, prd_folder, diff_folder, policy) -> list:
    """
    dev, prd, diffファイルのパスのリスト生成をする
    """
    paths = []
    for env_folder in os.listdir(dev_folder):
        dev_path = os.path.join(dev_folder, env_folder, policy)
        prd_path = os.path.join(prd_folder, env_folder, policy)
        diff_path = os.path.join(diff_folder, env_folder, policy)
        paths.append([dev_path, prd_path, diff_path])
    return paths


def create_rolegroup_paths(dev_folder, prd_folder, diff_folder, policy) -> list:
    """
    iam group, iam role ファイルのパスのリスト生成をする
    """
    rolegroup_paths = []
    policy_folders = create_folder_paths(dev_folder, prd_folder, diff_folder, policy)
    for policy_folder in policy_folders:
        compare_targets = find_compare_target(policy_folder[0], policy_folder[1])
        env_folder = policy_folder[0].split(os.path.sep)
        for target in compare_targets:
            dev_rolegroup_path = os.path.join(policy_folder[0], target[0])
            prd_rolegroup_path = os.path.join(policy_folder[1], target[1])
            diff_rolegroup_path = os.path.join(
                diff_folder, env_folder[-2], policy, target[0]
            )
            rolegroup_paths.append(
                [dev_rolegroup_path, prd_rolegroup_path, diff_rolegroup_path]
            )
    return rolegroup_paths


def read_file(file_path):
    """
    ファイルを読み込み、辞書を作成する
    """
    ref_dict = {}
    with open(file_path, "r", encoding=constants.CHARACODE_UTF8) as file:
        reader = csv.reader(file)
        for row in reader:
            ref_dict[row[1]] = row[0]
    return ref_dict


def add_exfile(target_dict, file_path):
    """
    ファイルを読み込み、辞書に追加する
    """
    with open(file_path, "r", encoding=constants.CHARACODE_UTF8) as file:
        reader = csv.reader(file)
        for row in reader:
            target_dict[row[1]] = row[0]
    return target_dict


def replace_value(data, ref_dict):
    """
    辞書内の文字列を置換する
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                for id, name in ref_dict.items():
                    if id in value:
                        data[key] = value.replace(id, name)
            elif isinstance(value, list):
                for i in range(len(value)):
                    if isinstance(value[i], str):
                        for id, name in ref_dict.items():
                            if id in value[i]:
                                value[i] = value[i].replace(id, name)
                    else:
                        replace_value(value[i], ref_dict)
            elif isinstance(value, dict):
                replace_value(value, ref_dict)
    elif isinstance(data, list):
        for i in range(len(data)):
            replace_value(data[i], ref_dict)
    return data


def find_compare_target(dev_path, prd_path) -> list:
    """
    差分検出するための比較対象ファイルのリスト作成
    """
    targets = []
    dev_file = None
    if os.path.isdir(dev_path) and os.path.isdir(prd_path):
        for file in os.listdir(prd_path):
            if file in os.listdir(dev_path):
                targets.append([file, file])
            elif "prd" in file:
                dev_file = file.replace("prd", "dev")
                if dev_file in os.listdir(dev_path):
                    targets.append([dev_file, file])
    return targets


def compare_policies(dev_path, prd_path, diff_path):
    """
    差分ファイルを生成する
    """
    html_diff = difflib.HtmlDiff()
    compare_targets = find_compare_target(dev_path, prd_path)
    for target in compare_targets:
        dev_policy_path = os.path.join(dev_path, target[0])
        prd_policy_path = os.path.join(prd_path, target[1])

        # 各種一覧ファイルの読み込み
        dev_accountid = read_file("./conf/dev_accountid.txt")
        prd_accountid = read_file("./conf/prd_accountid.txt")
        dev_vpcid = read_file("./list/dev_vpcid.txt")
        prd_vpcid = read_file("./list/prd_vpcid.txt")
        dev_sgid = read_file("./list/dev_securitygroupid.txt")
        prd_sgid = read_file("./list/prd_securitygroupid.txt")
        # 他環境の一覧ファイルの追加読み込み
        dev_accountid = add_exfile(dev_accountid, "./conf/ex/exdev_accountid.txt")
        prd_accountid = add_exfile(prd_accountid, "./conf/ex/exprd_accountid.txt")
        dev_sgid = add_exfile(dev_sgid, "./conf/ex/exdev_securitygroupid.txt")
        prd_sgid = add_exfile(prd_sgid, "./conf/ex/exprd_securitygroupid.txt")

        if os.path.isfile(dev_policy_path) and os.path.isfile(prd_policy_path):
            if dev_policy_path.endswith(".json") and prd_policy_path.endswith(".json"):
                # 開発/商用ポリシーの読み込み
                with open(dev_policy_path, "r") as dev_file:
                    dev_policy = json.load(dev_file)
                with open(prd_policy_path, "r") as prd_file:
                    prd_policy = json.load(prd_file)

                # AWSアカウントIDをアカウント名に置換
                dev_policy = replace_value(dev_policy, dev_accountid)
                prd_policy = replace_value(prd_policy, prd_accountid)
                # セキュリティグループIDをセキュリティグループ名に置換
                dev_policy = replace_value(dev_policy, dev_vpcid)
                prd_policy = replace_value(prd_policy, prd_vpcid)
                # VPCIDをVPC名に置換
                dev_policy = replace_value(dev_policy, dev_sgid)
                prd_policy = replace_value(prd_policy, prd_sgid)
                # 商用ポリシーにて"prd"を"dev"に置換
                env_dict = {"prd": "dev"}
                prd_policy = replace_value(prd_policy, env_dict)
                env_dict_Upper = {"Prd": "Dev"}
                prd_policy = replace_value(prd_policy, env_dict_Upper)

                # jsonのリスト部分に対して再度ソートをかける
                if "securitygroup" in dev_policy_path:
                    # ソート用キーを追加
                    dev_policy_addedkey_json_response = sort_functions.add_key(
                        dev_policy, constants.SORT_INFO_IN_SGRULE, constants.MERGED_KEY
                    )
                    # キーリストに基づいてソート
                    dev_policy_sortedaddedkey_json_response = (
                        sort_functions.sort_dict_in_list(
                            dev_policy_addedkey_json_response, constants.MERGED_KEY
                        )
                    )
                    # ソート用キーの削除
                    dev_policy_sorted_json_response = sort_functions.remove_key(
                        dev_policy_sortedaddedkey_json_response, constants.MERGED_KEY
                    )
                    # Tags内をソート
                    dev_policy_sorted_json_response = sort_functions.sort_dict_in_list(
                        dev_policy_sorted_json_response, "Key"
                    )
                else:
                    dev_policy_sorted_json_response = sort_functions.sort_policy(
                        dev_policy
                    )
                dev_policy_sorted_json_string = json.dumps(
                    dev_policy_sorted_json_response, indent=4
                )
                dev_policy = [
                    line + "\n" for line in dev_policy_sorted_json_string.splitlines()
                ]

                if "securitygroup" in prd_policy_path:
                    # ソート用キーを追加
                    prd_policy_addedkey_json_response = sort_functions.add_key(
                        prd_policy, constants.SORT_INFO_IN_SGRULE, constants.MERGED_KEY
                    )
                    # キーリストに基づいてソート
                    prd_policy_sortedaddedkey_json_response = (
                        sort_functions.sort_dict_in_list(
                            prd_policy_addedkey_json_response, constants.MERGED_KEY
                        )
                    )
                    # ソート用キーの削除
                    prd_policy_sorted_json_response = sort_functions.remove_key(
                        prd_policy_sortedaddedkey_json_response, constants.MERGED_KEY
                    )
                    # Tags内をソート
                    prd_policy_sorted_json_response = sort_functions.sort_dict_in_list(
                        prd_policy_sorted_json_response, "Key"
                    )
                else:
                    prd_policy_sorted_json_response = sort_functions.sort_policy(
                        prd_policy
                    )
                prd_policy_sorted_json_string = json.dumps(
                    prd_policy_sorted_json_response, indent=4
                )
                prd_policy = [
                    line + "\n" for line in prd_policy_sorted_json_string.splitlines()
                ]

            if target[0] == "Policy_List.txt":
                # 開発/商用ポリシーの読み込み
                with open(dev_policy_path, "r") as dev_file:
                    dev_policy = dev_file.read().splitlines()
                with open(prd_policy_path, "r") as prd_file:
                    prd_policy = prd_file.read().splitlines()
                # 商用ポリシーにて"prd"を"dev"に置換
                prd_policy = [line.replace("prd", "dev") for line in prd_policy]
                prd_policy = [line.replace("Prd", "Dev") for line in prd_policy]

                dev_policy.sort()
                dev_policy = [
                    s + "\n" if not s.endswith("\n") else s for s in dev_policy
                ]
                prd_policy.sort()
                prd_policy = [
                    s + "\n" if not s.endswith("\n") else s for s in prd_policy
                ]

            diff = difflib.unified_diff(
                dev_policy, prd_policy, fromfile=dev_policy_path, tofile=prd_policy_path
            )
            diff_text = "\n".join(diff)

            if diff_text:
                html_report = html_diff.make_file(
                    dev_policy,
                    prd_policy,
                    fromdesc=dev_policy_path,
                    todesc=prd_policy_path,
                )

                diff_file_path = os.path.join(diff_path, f"{target[0]}_diff.html")
                os.makedirs(diff_path, exist_ok=True)
                with open(
                    diff_file_path, "w", encoding=constants.CHARACODE_UTF8
                ) as report_file:
                    report_file.write(html_report)
