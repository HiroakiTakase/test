import boto3
import os
import json
from datetime import date, datetime

# デフォルトではData型をJson化できないため、文字列に変換する
def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def lambda_handler(event, context):
    if "image_name" not in event.keys():
        raise ValueError("`image_name` is not specified.")
    if "tag_team" not in event.keys():
        raise ValueError("`tag_team` is not specified.")
    if "tag_usage" not in event.keys():
        raise ValueError("`tag_usage` is not specified.")

    image_name = event["image_name"].lower()
    tag_team = event["tag_team"].lower()
    tag_usage = event["tag_usage"].lower()
    name_prefix = ("operation/", "official/", "custom/")
    if not image_name.startswith(name_prefix):
        raise ValueError("The value of `image_name` is invalid. It should start with one of {}".format(name_prefix))
    tags = ["common", "la"]
    if not tag_team in tags:
        raise ValueError("The value of `tag_team` is invalid. It should be one of {}.".format(tags))

    ecr = boto3.client(service_name="ecr",
                       endpoint_url=os.environ['ECR_ENDPOINT'])

    repo_response = ecr.create_repository(
        repositoryName=image_name,
        tags=[
            {"Key": "Team", "Value": tag_team},
            {"Key": "Usage", "Value": tag_usage},
        ],
        imageTagMutability="IMMUTABLE",
    )

    def get_policy():
      policy_tempalte = '''
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
      return policy_tempalte.replace('{account_id}', os.environ['ACCOUNT_ID'])

    policy_response = ecr.set_repository_policy(
      repositoryName=image_name,
      policyText=get_policy(),
      force=True
    )
    
    return  json.dumps(repo_response, default=json_serial)