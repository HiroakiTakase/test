#!/bin/bash

# ALERTの閾値設定
ALERT_EXEC=15
ALERT_CPU=5
ALERT_MEMORY=36864

# exec_listのコマンドについて
#「grep pyspark-shell」によりExecutorのポッドを抽出
#「awk '{print $1,$2}'」によりWS-IDとExecutorのPod名のみを抽出
#「cut -c 1-46」行の初めから46文字のみ抽出し数字による差異を無くす（例：ws-pji5kq1   pyspark-shell-7dea1486ee302a33-exec-9 の -9 を落とす）
#「uniq -c」で重複行をなくしながらExecutorの数を数えていく
# 最終的な形は「15 ws-pji5kq1 pyspark-shell-7dea1486ee302a33-exec」のようになる
kubectl get pods --all-namespaces | grep pyspark-shell > /tmp/pods_result
kubectl get pods --all-namespaces --selector=spark-role=executor -o json > /tmp/pod_detail
exec_list=$(< /tmp/pods_result awk '{print $1,$2}' | cut -c 1-46 | uniq -c | sort -rn)

# 最終的なアウトプットの格納先、列の先頭にそれぞれ文字列を配置
output=$(echo "$exec_list" | awk 'BEGIN{ OFS="\t"; print "利用者", "WS-ID", "プロセスID", "Executor数", "CPU設定値", "メモリ設定値"}')

# ヘッダー
results="\n★実行中ノートブックのPySpark設定が過剰なWS\n"

# 起動WSが一つもない場合のエラー回避
if [ -z "$exec_list" ]; then
    results+="起動中のWSがありません\n"
else
    # 取得した各行の設定情報を追加する処理
    while read -r line; do
        exec_num=$(echo "$line" | awk '{print $1}')
        namespace=$(echo "$line" | awk '{print $2}')
        exec_name=$(echo "$line" | awk '{print $3}')
        pod_name=$(< /tmp/pods_result grep "$namespace" | grep "$exec_name" | awk '{print $2}' | head -n 1 )
        target_pod=$(< /tmp/pod_detail jq -r '.items[]| select(.metadata.name=="'"${pod_name}"'")')
        username=$(echo "$target_pod" |jq -r '.metadata.labels.userName')
        cpu=$(echo "$target_pod" |jq -r '.spec.containers[] | select(.name == "spark-kubernetes-executor") | .env[] | select(.name == "SPARK_EXECUTOR_CORES") | .value')
        
        # メモリは「36864m」の表記であるため「m」を切り落とす
        memory=$(echo "$target_pod" |jq -r '.spec.containers[] | select(.name == "spark-kubernetes-executor") | .env[] | select(.name == "SPARK_EXECUTOR_MEMORY") | .value'| cut -f1 -d'm')

        # /tmp/pod_detailに問題があり、ユーザーネームの返り値が空だった場合の処理
        #　"ユーザーネームの取得に失敗しました"を送信文に加えループ処理を中断
        if [ -z "$username" ]; then
            output="${output}\nユーザーネームの取得に失敗しました"
            break

        # 基準を一つでも超えるノートブックがあれば出力する。
        elif [ "$exec_num" -gt "$ALERT_EXEC" ] || [ "$cpu" -gt "$ALERT_CPU" ] || [ "$memory" -gt "$ALERT_MEMORY" ]; then
            #p番からメンションに置き換え
            mail_add=$(grep -i "$username"$'\t' /tmp/p_name_list.tsv | head -n 1 | sed -E 's/\r//g;s/\n//g;'| awk -F '\t' '{print $2}')
            if [ "${mail_add}" != "" ]; then
                username=$mail_add"|"$username
            fi
            output="${output}\n${username}\t${namespace}\t${exec_name}\t${exec_num}\t${cpu}\t${memory}Mi"
        fi
    done <<< "$exec_list"

    # 調査の結果、異常な設定のノートブックがなければ出力はヘッダーのみ（1行）となるため、その場合は代わりに下記の文字を流す
    result_line=$(echo -e "$output" | grep -c ^) 
    if [ "$result_line" == 1 ]; then
        results+="該当のWSはありません\n"
    else
        results+="${output}\n"
    fi
fi

# exec_listのコマンドについて
# pyspark-shellであるExecutorのポッドリストファイルから
#「awk '{print $1}'」によりWS-IDのみを抽出
#「uniq -c」で重複行をなくしながらExecutorの数を数えていく
#「sort -rn」で降順にソートする
#「awk '$1 >= 50 {print}'」でExecutor数が50以上のWSをのみを取り出す。
# 最終的な形は「50 ws-pji5kq1」のようになる

ws_exec_list=$(< /tmp/pods_result awk '{print $1}' | uniq -c | sort -rn | awk '$1 >= 50 {print}')

# 最終的なアウトプットの格納先、列の先頭にそれぞれ文字列を配置
output=$(echo "$ws_exec_list" | awk 'BEGIN{ OFS="\t"; print "利用者", "WS-ID", "Executor数" }')

# ヘッダー
results+="\n\n★起動中のExecutor数が50以上のWS\n"

# 該当WSが一つもない場合のエラー回避
if [ -z "$ws_exec_list" ]; then
    results+="該当のWSはありません\n"
else
    # 取得した各行の設定情報を追加する処理
    while read -r line; do
        exec_num=$(echo "$line" | awk '{print $1}')
        namespace=$(echo "$line" | awk '{print $2}')
        
        pod_name=$(< /tmp/pods_result grep "$namespace" | grep pyspark-shell | awk '{print $2}' | head -n 1 )
        username=$(< /tmp/pod_detail jq -r '.items[]| select(.metadata.name=="'"${pod_name}"'")| .metadata.labels.userName')

        # /tmp/pod_detailに問題があり、ユーザーネームの返り値が空だった場合の処理
        #　"ユーザーネームの取得に失敗しました"を送信文に加えループ処理を中断
        if [ -z "$username" ]; then
            output="${output}\nユーザーネームの取得に失敗しました"
            break

        else    
            #p番からメンションに置き換え
            mail_add=$(grep -i "$username"$'\t' /tmp/p_name_list.tsv | head -n 1 | sed -E 's/\r//g;s/\n//g;'| awk -F '\t' '{print $2}')
            if [ "${mail_add}" != "" ]; then
                username=$mail_add"|"$username
            fi
            output="${output}\n${username}\t${namespace}\t${exec_num}"
        fi

    done <<< "$ws_exec_list"

    results+="${output}\n"
fi

# shellcheck disable=SC2086
echo $results
