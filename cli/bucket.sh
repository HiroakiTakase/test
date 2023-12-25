#!/bin/bash

# バケットポリシーを更新
aws s3api put-bucket-policy --bucket <bucket-name> --policy file://bucket-policy.json
