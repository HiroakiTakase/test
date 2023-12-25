#!/bin/bash

# インラインポリシーをJSONファイルをインプットにして更新
aws iam put-group-policy --group-name <group-name> --policy-name <policy-name> --policy-document file://policy.json
# インラインポリシーを削除
aws iam delete-group-policy --group-name <group-name> --policy-name <policy-name>
# ユーザー管理ポリシーを削除
aws iam detach-group-policy --group-name <group-name> --policy-arn arn:aws:iam::<account-id>:policy/<policy-name>
# AWS管理ポリシーを削除
aws iam detach-group-policy --group-name <group-name> --policy-arn arn:aws:iam::aws:policy/<policy-name>
# ユーザー管理ポリシーをアタッチ
aws iam attach-group-policy --group-name <group-name> --policy-arn arn:aws:iam::<account-id>:policy/<policy-name>
# AWS管理ポリシーをアタッチ
aws iam attach-group-policy --group-name <group-name> --policy-arn arn:aws:iam::aws:policy/<policy-name>

