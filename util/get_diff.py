"""
商用、開発差分ファイルを作成する
"""
import diff_functions
import sys


IAM_POLICY_LIST = ["iamgrouppolicy", "iamrolepolicy"]
SERVICE_POLICY_LIST = [
    "bucketpolicy",
    "iammanagedpolicy",
    "vpcepolicy",
    "kmspolicy",
    "securitygroup",
]
CREATE_DIFF_MSG = "Diff files creation is completed."
ERROR_DIFF_ARG_MSG = "Please specify a policy type. \nbucketpolicy, iammanagedpolicy, iamgrouppolicy, iamrolepolicy, vpcepolicy, kmspolicy or securitygroup"

if __name__ == "__main__":
    args = sys.argv
    if len(args) < 2:
        print(ERROR_DIFF_ARG_MSG)
        sys.exit(1)
    dev_folder = "./dev"
    prd_folder = "./prd"
    diff_folder = "./diff"
    policy = args[1]

    if args[1] in SERVICE_POLICY_LIST:
        policy_paths = diff_functions.create_folder_paths(
            dev_folder, prd_folder, diff_folder, policy
        )
        for policy_path in policy_paths:
            diff_functions.compare_policies(*policy_path)
        print(CREATE_DIFF_MSG)
    elif args[1] in IAM_POLICY_LIST:
        policy_paths = diff_functions.create_rolegroup_paths(
            dev_folder, prd_folder, diff_folder, policy
        )
        for policy_path in policy_paths:
            diff_functions.compare_policies(*policy_path)
        print(CREATE_DIFF_MSG)
    else:
        print(ERROR_DIFF_ARG_MSG)
