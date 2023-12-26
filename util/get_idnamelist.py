"""
引数で指定された環境に対してVPCとセキュリティグループの一覧を取得する
"""
import boto3
import botocore
import os
import sys
import common_functions
import constants


def save_vpc_mapping(session, filename):
    """
    VPCIDとVPC名のマッピング情報を取得し、ファイル出力する関数
    """
    try:
        vpc_id_name_mapping = {}
        client = session.client(constants.AWS_SERVICE_EC2)
        response = client.describe_vpcs()
        # VPC名の取得
        for vpc in response["Vpcs"]:
            vpc_id = vpc["VpcId"]
            vpc_name = "-"
            for tag in vpc.get("Tags", []):
                if tag["Key"] == "Name":
                    vpc_name = tag["Value"]
                    print("Get VPCinfo:", vpc_name)
                    break
            vpc_id_name_mapping[vpc_id] = vpc_name

        # VPC名でソート
        sorted_vpc_id_name_mapping = dict(
            sorted(vpc_id_name_mapping.items(), key=lambda x: x[1].lower())
        )

        with open(filename, "a") as f:
            for vpc_id, vpc_name in sorted_vpc_id_name_mapping.items():
                f.write(f"{vpc_name},{vpc_id}\n")

        return vpc_id_name_mapping

    except botocore.exceptions.ClientError as error:
        print(error)


def save_securitygroup_mapping(session, filename):
    """
    セキュリティグループIDとセキュリティグループ名のマッピング情報を取得し、ファイル出力する関数
    """
    try:
        sg_id_name_mapping = {}
        ec2_client = session.client(constants.AWS_SERVICE_EC2)
        response = ec2_client.describe_security_groups()
        # セキュリティグループ名の取得
        for security_group in response["SecurityGroups"]:
            sg_id = security_group["GroupId"]
            sg_name = security_group["GroupName"]
            sg_id_name_mapping[sg_id] = sg_name
            print("Get SGinfo:", sg_name)

        # セキュリティグループ名でソート
        sorted_sg_id_name_mapping = dict(
            sorted(sg_id_name_mapping.items(), key=lambda x: x[1].lower())
        )

        with open(filename, "a") as f:
            for sg_id, sg_name in sorted_sg_id_name_mapping.items():
                f.write(f"{sg_name},{sg_id}\n")

        return sorted_sg_id_name_mapping

    except botocore.exceptions.ClientError as error:
        print(error)


if __name__ == "__main__":
    args = sys.argv
    origin_profile_names = common_functions.get_origin_profile_names(args)

    # コマンド引数の正常性を判定
    common_functions.validate_command_arg(args, origin_profile_names)

    dir_path = "./list"
    os.makedirs(dir_path, exist_ok=True)
    # VPCIDとVPC名の一覧ファイルの新規作成
    vpcfilename = "./list/{0}_vpcid.txt".format(args[1])
    with open(vpcfilename, "w") as f:
        pass
    # セキュリティグループIDとセキュリティグループ名の一覧ファイルの新規作成
    sgfilename = "./list/{0}_securitygroupid.txt".format(args[1])
    with open(sgfilename, "w") as f:
        pass

    profile_names = common_functions.get_profile_names(args)
    for profile_name in profile_names:
        common_functions.print_profile_name(profile_name)
        try:
            session = boto3.Session(profile_name=profile_name)
            client = session.client(constants.AWS_SERVICE_EC2)
            response = client.describe_security_groups()

            # vpc IDとVPC名のマッピング情報の取得およびファイルの出力
            save_vpc_mapping(session, vpcfilename)

            # セキュリティグループIDとセキュリティグループ名のマッピング情報の取得およびファイルの出力
            save_securitygroup_mapping(session, sgfilename)
        except botocore.exceptions.ProfileNotFound:
            common_functions.print_profile_error(profile_name)
