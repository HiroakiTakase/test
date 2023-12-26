#!/bin/bash

# ALERTの閾値設定
ALERT_HOUR=24

# ws-が付くネームスペースにおける全てのPodをageの降順で表示し、6列目のageがd（48時間以上でd）またはh（3時間以上でh）のポッドを取得する
# 出力例 :「ws-pji5kq1    pyspark-shell-7dea1486ee302a33-exec-9    1/1    Running    0   36h」
# apiコールの数を減らすためラベルがそれぞれworkspace, executorのpod情報リストをjson形式で一時ファイルに格納
kubectl get pods --all-namespaces --sort-by=.status.startTime | grep "^ws-" | awk '{if ($6 ~ /d|h/) print $0}' > /tmp/pods_result
kubectl get pods --all-namespaces --selector=app=workspace -o json > /tmp/ws_detail
kubectl get pods --all-namespaces --selector=spark-role=executor -o json > /tmp/exec_detail

# pos_resultにはworkspaceとexecutorのPodが混在しているため、workspaceのみを抽出
ws_list=$(< /tmp/pods_result grep "workspace" | awk '{print $1,$2,$6}' )

# 最終的なアウトプットの格納先、列の先頭にそれぞれ文字列を配置
output=$(echo "$ws_list" | awk 'BEGIN{ OFS="\t"; print "利用者", "WS-ID", "起動時間"}')

# ヘッダー
results="\n★起動時間が24時間を越えるWS\n"

# 起動WSが一つもない場合のエラー回避
if [ -z "$ws_list" ]; then
    results+="該当のWSがありません\n"
else
    # 取得した各行の情報を変数に追加する処理
    while read -r line; do
        namespace=$(echo "$line" | awk '{print $1}')
        pod_name=$(echo "$line" | awk '{print $2}')
        age=$(echo "$line" | awk '{print $3}')

        #age内にhがあるかどうかで振り分け
        hour=''
        if [[ $age =~ ([0-9]+)h ]]; then
            hour="${BASH_REMATCH[1]}"
        fi

        # hourが基準を超えれば通知をする、dの場合はhourが空となり無条件で通知するようにする
        if [ -z "$hour" ] || [ "$hour" -gt "$ALERT_HOUR" ] ; then
            #_num_list.tsvを参照してp番からメールアドレスを取得する
            target_pod=$(< /tmp/ws_detail jq -r '.items[]| select(.metadata.namespace=="'"${namespace}"'")')
            username=$(echo "$target_pod" |jq -r '.metadata.labels.userName')
            mail_add=$(grep -i "$username"$'\t' /tmp/p_name_list.tsv | head -n 1 | sed -E 's/\r//g;s/\n//g;'| awk -F '\t' '{print $2}')

            # /tmp/pod_detailに問題があり、ユーザーネームの返り値が空だった場合の処理
            #　"ユーザーネームの取得に失敗しました"を送信文に加えループ処理を中断
            if [ -z "$username" ]; then
                output="${output}\nユーザーネームの取得に失敗しました"
                break

            elif [ "${mail_add}" != "" ]; then
                username=$mail_add"|"$username
            fi
            output="${output}\n${username}\t${namespace}\t${age}"
        fi
    done <<< "$ws_list"

    # 調査の結果、24時間以上連続起動中のWSがなければ出力はヘッダーのみ（1行）となるため、その場合は代わりに下記の文字を流す
    result_line=$(echo -e "$output" | grep -c ^) 
    if [ "$result_line" == 1 ]; then
        results+="該当のWSはありません\n"
    else
        results+="${output}\n"
    fi
fi


# pods_resultにはworkspaceとexecutorのPodが混在しているため、executorのみを抽出
# 下記以降ではWSと同じ処理を実行
exec_list=$(< /tmp/pods_result grep "pyspark-shell" | awk '{print $1,$2}' | cut -c 1-46 | uniq)

output=$(echo "$exec_list" | awk 'BEGIN{ OFS="\t"; print "利用者", "WS-ID", "起動時間"}')

results+="\n★起動時間が24時間を越えるExecutorを持つWS\n"

# 起動WSが一つもない場合のエラー回避
if [ -z "$exec_list" ]; then
    results+="\n該当のWSがありません\n"

else
    while read -r line; do
        namespace=$(echo "$line" | awk '{print $1}')
        exec_name=$(echo "$line" | awk '{print $2}')
        age=$(< /tmp/pods_result grep "$exec_name" | awk '{print $6}' | head -n 1)
        pod_name=$(< /tmp/pods_result grep "$exec_name" | awk '{print $2}' | head -n 1 )

        hour=''
        if [[ $age =~ ([0-9]+)h ]]; then
            hour="${BASH_REMATCH[1]}"
        fi

        if [ -z "$hour" ] || [ "$hour" -gt "$ALERT_HOUR" ] ; then
            target_pod=$(< /tmp/exec_detail jq -r '.items[]| select(.metadata.name=="'"${pod_name}"'")')
            username=$(echo "$target_pod" |jq -r '.metadata.labels.userName')
            mail_add=$(grep -i "$username"$'\t' /tmp/p_name_list.tsv | head -n 1 | sed -E 's/\r//g;s/\n//g;'| awk -F '\t' '{print $2}')

            # /tmp/pod_detailに問題があり、ユーザーネームの返り値が空だった場合の処理
            #　"ユーザーネームの取得に失敗しました"を送信文に加えループ処理を中断
            if [ -z "$username" ]; then
                output="${output}\nユーザーネームの取得に失敗しました"
                break

            elif [ "${mail_add}" != "" ]; then
                username=$mail_add"|"$username
            fi
            output="${output}\n${username}\t${namespace}\t${age}"
        fi
    done <<< "$exec_list"

    result_line=$(echo -e "$output" | grep -c ^) 
    if [ "$result_line" == 1 ]; then
        results+="該当のWSはありません\n"
    else
        results+="\n${output}\n"
    fi
fi

# shellcheck disable=SC2086
echo $results