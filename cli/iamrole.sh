#!/bin/bash

# ユーザー管理ポリシーをアタッチ
aws iam attach-role-policy --role-name <role-name> --policy-arn arn:aws:iam::<account-id>:policy/<policy-name>
# AWS管理ポリシーをアタッチ
aws iam attach-role-policy --role-name <role-name> --policy-arn arn:aws:iam::aws:policy/<policy-name>
# ユーザー管理ポリシーを削除
aws iam detach-role-policy --role-name <role-name> --policy-arn arn:aws:iam::<account-id>:policy/<policy-name>
# AWS管理ポリシーを削除
aws iam detach-role-policy --role-name <role-name> --policy-arn arn:aws:iam::aws:policy/<policy-name>
# インラインポリシーをJSONファイルをインプットにして更新
aws iam put-role-policy --role-name <role-name> --policy-name <policy-name> --policy-document file://policy.json
# インラインポリシーを削除
aws iam delete-role-policy --role-name <role-name> --policy-name <policy-name>
# 信頼ポリシーを更新
aws iam update-assume-role-policy --role-name <role-name> --policy-document file://trust-policy.json
