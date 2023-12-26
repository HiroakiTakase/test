import boto3
import os
from botocore.exceptions import ClientError


def get_policy():
    policy_template = '''
    {
        "Version": "2008-10-17",
        "Statement": [
          {
            "Sid": "AllowAccessFromOpenanalysisEnv",
            "Effect": "Allow",
            "Principal": {
              "AWS": "arn:aws:iam::{account_id}:root"
            },
            "Action": [
              "ecr:BatchCheckLayerAvailability",
              "ecr:BatchDeleteImage",
              "ecr:BatchGetImage",
              "ecr:CompleteLayerUpload",
              "ecr:DeleteLifecyclePolicy",
              "ecr:DescribeImages",
              "ecr:DescribeRepositories",
              "ecr:GetDownloadUrlForLayer",
              "ecr:GetLifecyclePolicy",
              "ecr:GetLifecyclePolicyPreview",
              "ecr:GetRepositoryPolicy",
              "ecr:InitiateLayerUpload",
              "ecr:ListImages",
              "ecr:PutImage",
              "ecr:PutLifecyclePolicy",
              "ecr:StartLifecyclePolicyPreview",
              "ecr:UploadLayerPart",
              "ecr:DeleteRepository"
            ]
          },
          {
            "Sid": "DenyPolicyUpdate",
            "Effect": "Deny",
            "NotPrincipal": {
              "AWS": [
                "arn:aws:iam::{account_id}:root",
                "arn:aws:iam::{account_id}:user/ecrmnt-user"
              ]
            },
            "Action": [
              "ecr:DeleteRepositoryPolicy",
              "ecr:SetRepositoryPolicy"
            ]
          }
        ]
    }
    '''
    return policy_template.replace('{account_id}', os.environ['ACCOUNT_ID'])


def lambda_handler(event, context):

    if "unit_name" not in event.keys() or event["unit_name"].strip() == "":
        raise ValueError("`unit_name` is not specified.")

    if "p_num" not in event.keys() or event["p_num"].strip() == "":
        raise ValueError("`p_num` is not specified.")

    if "usage" not in event.keys() or event["usage"].strip() == "":
        raise ValueError("`usage` is not specified.")

    if "image_name" not in event.keys() or event["image_name"].strip() == "":
        raise ValueError("`image_name` is not specified.")

    unit_name = event["unit_name"]
    p_num = event["p_num"]
    usage = event["usage"]
    image_name = event['image_name']
    repository_name = "terrasium-user-images" + "/" + usage + "/" + image_name

    client = boto3.client("ecr")

    try:
        response = client.create_repository(
            repositoryName=repository_name,
            tags=[
                {
                    'Key': 'Project',
                    'Value': os.environ['ENV'] + '-eksanalysis'
                },
                {
                    'Key': 'Name',
                    'Value': os.environ['ENV'] + '-eksanalysis-terrasium-ecr-repository'
                },
                {
                    'Key': 'Team',
                    'Value': unit_name
                },
                {
                    'Key': 'EmployeeNum',
                    'Value': p_num
                },
                {
                    'Key': 'Usage',
                    'Value': 'terrasium-eks'
                }
            ],
            imageTagMutability="IMMUTABLE"
        )

        client.set_repository_policy(
            repositoryName=repository_name,
            policyText=get_policy(),
            force=True
        )

        response_txt = "ECR repository is created. (path:" + response["repository"]["repositoryUri"] + ")"

        return response_txt

    except ClientError as e:
        raise e
