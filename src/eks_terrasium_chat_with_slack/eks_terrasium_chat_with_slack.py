import os
import boto3
from slack_sdk import WebClient


# 巡回結果であるpayloadのメッセージを各行パースし、分析者メールアドレスがあればメンションに置き換える関数
def add_mention_to_messsage(client: str, message: str) -> str:
    """
    EKS過剰スペックWSの通知について、
    下記の出力内容にメールをメンションに置き換える場合、lenが3or6であるかを条件として洗い出す

    （\tで分割している対象の行）
    ・ノートブック単位で過剰リソースを設定しているワークスペース一覧
    担当者 ワークスペースID プロセスID executors数 CPU設定値 メモリ設定値
    xxxxx@xxxxx|p1111 ws-i7wmqel  pyspark-shell-a0e1f688b8d1aec3-exec 20  3   22528Mi

    ・起動中のexecutor数値が50を超過しているワークスペース一覧
    担当者 ワークスペースID executor数
    xxxxx@xxxxx|p1111 ws-i7wmqel  20
    """

    text = ""  # 返り値用の空テキストを準備
    for line in message.splitlines():
        line_detail = line.split("\t")

        # 分析者が検挙された行は一行の要素数が3または6になるため、その場合に下記の処理を実施
        if len(line_detail) == 3 or len(line_detail) == 6:
            if "@" in line_detail[0]:
                # xxxxx@xxxxx|p1111 をパイプで分割してリストとしてp_num_mailに格納
                p_num_mail = line_detail[0].split("|")
                email = p_num_mail[0]
                user_info = client.users_lookupByEmail(email=email)

                if "user" in user_info:  # メールアドレスからSlackのユーザー情報が参照できればユーザーIDに変換
                    line_detail[0] = "<@" + user_info["user"]["id"] + ">"
                else:  # 参照できなければそのままP番を使用
                    line_detail[0] = p_num_mail[1]
            line = "\t".join(line_detail)

        text = text + line + "\n"
    return text


# パラメーターストアからシークレットキー（パスワード）取得をする関数
# 本スクリプトではSLACK_BOT_TOKENを取得するために用いる
def get_parameters(secret_name: str) -> str:
    ssm = boto3.client("ssm")
    response = ssm.get_parameters(Names=[secret_name], WithDecryption=True)

    # 取得したシークレットが含まれる全文からfor文でシークレットを取り出す
    for parameter in response["Parameters"]:
        return parameter["Value"]


# 先頭の投稿をする関数
def post_message(client: str, channel: str, text: str) -> dict:
    response = client.chat_postMessage(channel=channel, text=text)
    return response


# スレッドにメッセージを投稿する関数
def post_thread_message(client: str, channel: str, text: str, thread_ts: float) -> dict:
    response = client.chat_postMessage(channel=channel, text=text, thread_ts=thread_ts)
    return response


def lambda_handler(event, context):
    # シークレットマネージャーを使用してSLACK_BOT_TOKENを取得します
    secret_name = "arise_slack_bot_token_kms"
    BOT_TOKEN = get_parameters(secret_name)

    # 投稿に必要な各種引数の準備
    client = WebClient(token=BOT_TOKEN)
    channel = os.environ["CHANNEL"]
    text = event["message"]

    # .shファイルから提供されるpayloadのメッセージが空の場合のエラー処理
    if "message" not in event.keys() or event["message"].strip() == "":
        raise ValueError("`message` is not specified")

    # 投稿に関する部分、payloadの"post_type"により先頭の投稿 or スレッドへの投稿で場合分け
    if event["post_type"] == "main":
        response = post_message(client, channel, text)
        return response["ts"]

    if event["post_type"] == "thread":
        text = add_mention_to_messsage(client, text)
        thread_ts = event["thread_ts"]  # 返信対象のtsをpayloadから取得
        response = post_thread_message(client, channel, text, thread_ts)
        return response["ts"]
