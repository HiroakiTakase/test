#!/bin/bash
function lambda_handler () {
    aws s3 cp s3://kddi-dmp-dev-analytics-work/ao/p_num_list/data.tsv /tmp/p_name_list.tsv

    aws eks list-clusters --query 'clusters' |grep -E "$ENV"'-eksanalysis.*-cluster'|sed -e 's/"//g' -e 's/ //g' -e 's/,//g'|sort -rn > /tmp/cluster_list

    mail_body+="ご利用中のWS（ワークスペース）もしくは分析処理に使用中のExecutorが24時間を超えて継続起動をしているため連絡をさせていただきました:male-police-officer:\n\n"
    mail_body+="WSについてはオチロー君ありきとしたご利用を避け、処理が終わったら手動停止をするようお願い致します！\n"
    mail_body+="※Airflowのジョブ実行はWSを起動する必要はありません。無駄なコストとなるのでAirflow実行のためにWS起動しておくのはお避けください:money_with_wings:\n\n"
    mail_body+="Executorで検出された方は長期間連続実行中のSpark処理にお心当たりはございませんか？起動中のExecutorはGrafanaにて確認が可能なのでチェックをお願いします。\n"
    mail_body+="もし該当のExecutorが不要であれば消去させていただきますのでこちらのスレッドで @tcs-operator をつけてご連絡下さい:bows::yorosiku_onegai:\n\n"
    
    while IFS= read -r line;do
        if [ -e /tmp/kubeconfig ]; then
            rm /tmp/kubeconfig
        fi
        aws eks update-kubeconfig --name "$line"
        mail_body+="\n************${line}************\n "
        mail_body+=$("./get_pod_age.sh")
    done < /tmp/cluster_list

    # get_pod_age.shでユーザーネームの取得を失敗した場合の処理
    # 送信文中に"ユーザーネームの取得に失敗しました"があったら自動終了をする
    if [[ $mail_body == *"ユーザーネームの取得に失敗しました"* ]]; then
        echo "ユーザーネームの取得に失敗しました。スクリプトを中断します。"
        exit 0
    fi

    aws --cli-binary-format raw-in-base64-out lambda invoke --function-name eks_terrasium_chat_with_slack --payload '{"message": ":alarm: 長期継続リソース24時 :alarm:", "post_type": "main", "thread_ts": "" }'  --region ap-northeast-1 /tmp/response.json
    thread_ts=$(< /tmp/response.json head -n 1 | sed -e 's/"//g')
    aws --cli-binary-format raw-in-base64-out lambda invoke --function-name eks_terrasium_chat_with_slack --payload '{"message": "'"$mail_body"'", "post_type": "thread", "thread_ts": "'"$thread_ts"'" }' --region ap-northeast-1 /tmp/response.json

}
