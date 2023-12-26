import json
import boto3
import os
import datetime

TOPIC_ARN = os.environ["TOPIC_ARN"]


def lambda_handler(event, context):
    now = datetime.datetime.now()
    end_time = datetime.datetime(
        now.year, now.month, now.day, now.hour, now.minute, now.second, 0
    )
    start_time = end_time - datetime.timedelta(minutes=60)
    end_time_unix = int(end_time.timestamp() * 1000)
    start_time_unix = int(start_time.timestamp() * 1000)

    client = boto3.client("logs")
    sns = boto3.resource("sns")

    clusters = []
    cluster_list = boto3.client("eks")
    cluster_list_res = cluster_list.list_clusters()
    cluster_list_res["clusters"].sort(reverse=True)

    for val in cluster_list_res["clusters"]:
        if val.startswith(os.environ["ENV"] + "-eksanalysis") and val.endswith(
            "-cluster"
        ):
            clusters.append(val)

    results = ""

    for cluster in clusters:
        results += "*" * 30
        results += cluster + "\n"

        response = client.filter_log_events(
            logGroupName=cluster,
            logStreamNamePrefix="fluentbit-kube.var.log.containers.get-efs-usage-under-",
            startTime=start_time_unix,
            endTime=end_time_unix,
        )

        print(response.get("events"))

        search_string = "F GET_EFS_USAGE"

        for t in response.get("events"):
            target_string = json.loads(t.get("message")).get("log")

            if search_string in target_string:
                print(target_string)

                # search_stringの後続文字列を出力
                start_index = target_string.index(search_string) + len(search_string)
                result = target_string[start_index:].strip()
                print(result)

                results += result + "\n"

        while "nextToken" in response.keys():
            currentToken = response["nextToken"]

            response = client.filter_log_events(
                logGroupName=cluster,
                logStreamNamePrefix="fluentbit-kube.var.log.containers.get-efs-usage-under-",
                startTime=start_time_unix,
                endTime=end_time_unix,
                nextToken=currentToken,
            )

            print(response.get("events"))

            for t in response.get("events"):
                target_string = json.loads(t.get("message")).get("log")

                if search_string in target_string:
                    print(target_string)

                    # search_stringの後続文字列を出力
                    start_index = target_string.index(search_string) + len(
                        search_string
                    )
                    result = target_string[start_index:].strip()
                    print(result)

                    results += result + "\n"

    print(results)
    subject = "EFS利用状況通知"
    sns.Topic(TOPIC_ARN).publish(Message=str(results), Subject=subject)

    return {"statusCode": 200, "body": json.dumps(results)}
