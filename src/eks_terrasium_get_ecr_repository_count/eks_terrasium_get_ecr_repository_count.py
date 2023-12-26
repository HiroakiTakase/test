import boto3
from botocore.exceptions import ClientError


def lambda_handler(event, context):
    client = boto3.client("ecr")
    try:
        result = []
        res = client.describe_repositories()
        result += res["repositories"]
        # 1回のAPIで最大100個のリポジトリが返却できる
        while "nextToken" in res.keys():
            curToken = res["nextToken"]
            res = client.describe_repositories(nextToken=curToken)
            result += res["repositories"]

        if len(result) >= 9800:
            print("ERROR: ECRリポジトリ数が9800を超えました。（上限：10000）")
            return 1
        else:
            return 0

    except ClientError as e:
        raise e
