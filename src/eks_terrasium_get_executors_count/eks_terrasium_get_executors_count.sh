#!/bin/bash
function lambda_handler () {
    aws eks list-clusters --query 'clusters' |grep -E "$ENV"'-eksanalysis.*-cluster'|sed -e 's/"//g' -e 's/ //g' -e 's/,//g'|sort -rn > /tmp/cluster_list

    while IFS= read -r line;do
        if [ -e /tmp/kubeconfig ]; then
            rm /tmp/kubeconfig
        fi
        aws eks update-kubeconfig --name "$line"
        mail_body+=$(echo -e "\n\n\n--------------------------$line------------------------")
        mail_body+=$('./get-spark-workspace-spec.sh')
    done < /tmp/cluster_list

    aws sns publish \
        --topic-arn "$TOPIC_ARN" \
        --message "$mail_body" \
        --subject "Spotノード使用率90%超過アラーム発生時のSpark Executor数一覧"

}
