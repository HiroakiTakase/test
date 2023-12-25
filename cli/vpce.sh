#!/bin/bash

# VPCエンドポイントポリシーを更新
aws ec2 modify-vpc-endpoint --vpc-endpoint-id <vpc-endpoint-id> --policy-document file://endpoint-policy.json
# VPCエンドポイントIDを取得
aws ec2 describe-vpc-endpoints --filters "Name=tag:Name,Values=<tag-value>" --query 'VpcEndpoints[].VpcEndpointId' --output text

