#!/bin/bash

# こちらがLambdaの実行ファイルとなっている

function lambda_handler () {
    # まずP番をメンションに変換するための参照リスト（tsvファイル）をS3から一時ファイルとしてコピー
    aws s3 cp s3://kddi-dmp-"$ENV"-analytics-work/ao/p_num_list/data.tsv /tmp/p_name_list.tsv

    # リソース調査対象のクラスター名を取得、リストにして一時ファイルとして保存
    aws eks list-clusters --query 'clusters' |grep -E "$ENV"'-eksanalysis.*-cluster'|sed -e 's/"//g' -e 's/ //g' -e 's/,//g'|sort -rn > /tmp/cluster_list

    # 送信テキスト本文を作成
    mail_body+="ご利用中のWS（ワークスペース）におけるPySpark実行リソース設定に過剰な数値が検出されたため連絡させていただきました:female-police-officer:\n"
    mail_body+="Terrasiumでは他の分析者と分析環境のリソースを共有する仕様となっているため、一人で一度に大量のリソースを占有すると他の分析者へ影響がある可能性があります。過剰なリソース占有を防止するため、下記設定値を超えての利用が必要な場合は個別に @tcs-operator までご連絡ください:bows::yorosiku_onegai:\n\n"
    mail_body+="・spark.executor.cores : 5\n"
    mail_body+="・spark.executor.memory : 36G\n"
    mail_body+="・spark.dynamicAllocation.maxExecutors : 15\n"
    mail_body+="・WS単位で同時実行可能なExecutor数 : 50\n\n"

    # クラスター1, 2に対してそれぞれ、get-spark-notebook-workspace-spec.shを実行して結果を送信テキストに追記
    while IFS= read -r line;do
        if [ -e /tmp/kubeconfig ]; then
            rm /tmp/kubeconfig
        fi
        aws eks update-kubeconfig --name "$line"
        mail_body+="\n************${line}************\n "
        mail_body+=$("./get-spark-notebook-workspace-spec.sh")
    done < /tmp/cluster_list
    
    # get-spark-notebook-workspace-spec.shでユーザーネームの取得を失敗した場合の処理
    # 送信文中に"ユーザーネームの取得に失敗しました"があったら自動終了をする
    if [[ $mail_body == *"ユーザーネームの取得に失敗しました"* ]]; then
        echo "ユーザーネームの取得に失敗しました。スクリプトを中断します。"
        exit 0
    fi
    
    # Slackの送信部分、投稿用のLambda関数であるchat_with_slackにテキストを渡して送信する
    # チャンネルに長文を送らないようにするため、初めにスレッドを作成
    aws --cli-binary-format raw-in-base64-out lambda invoke --function-name eks_terrasium_chat_with_slack --payload '{"message": ":alarm: リソース警察巡回日報 :alarm:", "post_type": "main", "thread_ts": "" }' --region ap-northeast-1 /tmp/response.json
    # 作成スレッドのタイムスタンプを格納
    thread_ts=$(< /tmp/response.json head -n 1 | sed -e 's/"//g')
    # 格納したタイムスタンプを基に、スレッドに日報の本文を投稿
    aws --cli-binary-format raw-in-base64-out lambda invoke --function-name eks_terrasium_chat_with_slack --payload '{"message": "'"$mail_body"'", "post_type": "thread", "thread_ts": "'"$thread_ts"'" }' --region ap-northeast-1 /tmp/response.json

}
