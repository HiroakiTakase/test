import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import openai
import langchain
from langchain.prompts import load_prompt
import json

load_dotenv()
app = App(token=os.environ["SLACK_BOT_TOKEN"])
openai.api_type = "azure"
openai.api_version = "2023-05-15"
openai.api_key = os.environ["OPENAI_API_KEY"]
openai.api_base = "https://slackchatbot.openai.azure.com/"

# TODO
# json読み込み
with open("./test.json") as f:
    test = json.load(f)


# 会話履歴の作成関数
def create_chat_history(response, thread_ts, system_message):
    """
    Create a message for ChatGPT API from the thread content.
    If app_id is present, it is assumed to be a response from ChatGPT,
    set "assistant" role. If not, set "user" role.
    """
    content = {
        "role": "system",
        "content": system_message,
    }  # 会話履歴の先頭につけるChatGPTの性格設定
    chat_history = {thread_ts: {"message": [content]}}  # 会話履歴の格納先

    for res in response.data["messages"]:
        app_id = res.get("app_id")
        role = "assistant" if app_id else "user"
        text = res.get("text")
        if not app_id:
            text = text.replace("<@U03QQN7E74Y>", "")  # Chatbotへのメンションを削除
        content = {"role": role, "content": text}
        chat_history[thread_ts]["message"].append(content)  # chat_historyへ会話を格納

    return chat_history


@app.event("app_mention")
def chatgpt_reply(event, say):
    # 投稿に関する情報の取得
    input_message = event["text"]
    input_message = input_message.replace(
        "<@U03QQN7E74Y>", ""
    )  # Chatbotへのメンションを削除して整理
    print("prompt: " + input_message)  # ログへ流す

    channel = event["channel"]

    if "thread_ts" not in event:  # 初回の投稿かどうかでタイムスタンプの取得先を変える
        thread_ts = event["ts"]  # 初回
    else:
        thread_ts = event["thread_ts"]  # 2回目以降

    # TODO
    # ChatGPTの性格設定
    # system_message = "You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible."
    # system_message = "あなたは侍です。侍風に答えてください。"
    system_message = test["template"]
    # 会話履歴の作成
    response = app.client.conversations_replies(channel=channel, ts=thread_ts)
    chat_history = create_chat_history(response, thread_ts, system_message)
    chat_history = chat_history[thread_ts]["message"]  # メッセージ部分の取り出し

    # ChatGPTのリクエスト（会話型リクエスト）の作成
    response = openai.ChatCompletion.create(
        deployment_id="slack_bot",
        messages=chat_history,  # デプロイメントの指定
    )
    text = response["choices"][0]["message"]["content"]  # ChatGPTの返答を取得
    print("ChatGPT: " + text)  # ログに表示

    # スレッド内に返信
    say(text=text, thread_ts=thread_ts, channel=channel)


# 邪魔なログ Unhandled request ({'type': 'event_callback', 'event': {'type': 'message'}}) の表示回避
@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)


# アプリを起動
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
