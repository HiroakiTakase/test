#!/bin/bash

# VPCエンドポイントポリシーを更新
aws iam create-policy-version --policy-arn arn:aws:iam::<account-id>:policy/<policy-name> --policy-document file://policy.json --set-as-default
