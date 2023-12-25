import os
import sys

ERROR_CMD_ARG_ENV = "Please specify 'dev' or 'prd' as the environment."
ERROR_CMD_ARG_PROFILE = "Please specify a valid profile name."


def get_origin_profile_names(args):
    """
    アクセス先環境プロファイル名のリストを作成する
    """
    if args[1] == "dev":
        with open('./conf/dev_accountid.txt', 'r') as file:
            lines = file.readlines()

        profile_list = [line.split(',')[0] for line in lines]

        return profile_list
    elif args[1] == "prd":
        with open('./conf/prd_accountid.txt', 'r') as file:
            lines = file.readlines()

        profile_list = [line.split(',')[0] for line in lines]

        return profile_list
    else:
        print(ERROR_CMD_ARG_ENV)
        sys.exit(1)


def get_origin_profile_name(profile_name):
    origin_profile = profile_name.split('-')[1]

    return origin_profile


def print_profile_name(profile_name):
    print('=== Profile {} ==='.format(profile_name))

    return


def print_profile_error(profile_name):
    print(f"Profile not found: {profile_name}.")

    return


def validate_command_arg(args, origin_profile_names):
    """
    受け取ったコマンド引数の正常性判定する
    """
    if len(args) < 2:
        print(ERROR_CMD_ARG_ENV)
        sys.exit(1)

    # 引数指定がprd/devのみの場合の判定
    env = args[1]
    if len(args) == 2:
        if env in ["dev", "prd"]:
            return
        else:
            print(ERROR_CMD_ARG_ENV)
            sys.exit(1)

    # 引数にprd/devとprofile指定がある場合の判定
    specific_profile = args[2]
    if len(args) == 3:
        if specific_profile in origin_profile_names:
            return
        else:
            print(ERROR_CMD_ARG_PROFILE)
            sys.exit(1)


def get_profile_names(args):
    """
    「dev-」または「prd-」のプレフィックス付きProfileリストを取得する
    """
    if len(args) == 2:
        origin_profiles = get_origin_profile_names(args)
        profile_names = []
        for i in origin_profiles:
            profile_names.append(args[1] + "-" + i)
        return profile_names
    elif len(args) == 3:
        profile_names = []
        profile_names.append(args[1] + "-" + args[2])
        return profile_names
