import boto3
import os
import time
import json
import re
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta

START_LINE = "******************************start******************************************" + "\n"
LINE = "\n" + "************************************************************************"
END_LINE = "\n" + "******************************end******************************************"
REGION = "ap-northeast-1"
# ログ名のprefix
LOG_STREAM_NAME_PREFIX = "fluentbit-kube.var.log.containers.cronjob-kubectl-cost-"
# 1時間（単位：milliseconds）
BATCH_EXECUTE_PERIOD = 3600000
# snsのarn
TOPIC_ARN = os.environ['TOPIC_ARN']


# CostExplorerからのレスポンスを整形
def response_format(response_context: str, type="normal", report_type="week") -> str:
    title = []
    memberlist_y_title = []
    title_week = ""
    # ヘッダー作成
    for key in range(len(response_context['ResultsByTime'])):
        if type == "memberList":
            if key == 0 or report_type != "week":
                title.append(response_context['ResultsByTime'][key]["TimePeriod"]["Start"])
                title_week = (response_context['ResultsByTime'][key]["TimePeriod"]["Start"])
        for val in response_context['ResultsByTime'][key]['Groups']:
            if type == "normal":
                title.append(val['Keys'][0])
            else:
                memberlist_y_title.append(val['Keys'][0][12:])  # P番大文字対応

    if len(title) > 0:
        if type == "normal":
            title = ["TimePeriod"] + list(set(title))
        else:
            title = ["TimePeriod"] + title

    if len(memberlist_y_title) > 0:
        memberlist_y_title = list(set(memberlist_y_title))

    context = []
    context_tmp_member = {}
    for key in range(len(response_context['ResultsByTime'])):
        context_tmp = {}
        context_tmp["TimePeriod"] = response_context['ResultsByTime'][key]["TimePeriod"]["Start"]
        for val in response_context['ResultsByTime'][key]['Groups']:
            if type == "normal":
                context_tmp[val['Keys'][0]] = val['Metrics']['UnblendedCost']['Amount']
            else:
                context_tmp[val['Keys'][0][12:]] = val['Metrics']['UnblendedCost']['Amount']  # P番大文字対応
            if report_type == "week":
                if val['Keys'][0][12:] in context_tmp_member:
                    context_tmp_member[val['Keys'][0][12:]] += \
                        float(val['Metrics']['UnblendedCost']['Amount'])
                else:
                    context_tmp_member[val['Keys'][0][12:]] = \
                        float(val['Metrics']['UnblendedCost']['Amount'])
        context.append(context_tmp)

    # 月跨ぎの場合、週次にEMR料金（CA/MA/MS/DDUチーム）-P番別料金を１列にする
    if len(memberlist_y_title) > 0 and report_type == "week":
        context = []
        for item in memberlist_y_title:
            context_tmp = {}
            context_tmp["TimePeriod"] = title_week
            if item in context_tmp_member:
                context_tmp[item] = context_tmp_member[item]
            context.append(context_tmp)

    output_list = []
    # 出力メッセージ作成
    if type == "normal":
        for val in context:
            output_list_per = []
            for item in title:
                if item in val:
                    output_list_per.append(val[item])
                else:
                    output_list_per.append("")
            output_list.append(",".join(str(n) for n in output_list_per))
    else:
        for item in memberlist_y_title:
            output_list_per = []
            output_list_per.append(item)
            for title_item in title:
                if title_item == "TimePeriod":
                    continue
                for context_item in context:
                    if report_type != "week":
                        if title_item == context_item["TimePeriod"]:
                            if item in context_item:
                                output_list_per.append(context_item[item])
                            else:
                                output_list_per.append("")
                    else:
                        if item in context_item:
                            if title_item == context_item["TimePeriod"]:
                                output_list_per.append(context_item[item])
                            else:
                                output_list_per.append("")
            output_list.append(",".join(str(n) for n in output_list_per))
    return {"title": title, "output_list": output_list}

# p番またはs番を大文字にする 例)p1111 → P1111
def convert_to_upper_case(word: str) -> str:
    if word[0] in 'ps' and word[1:].isdigit():
        return word[0].upper() + word[1:]
    else:
        return word

# メール送信
def send_mail(subject: str, message: str) -> None:
    sns = boto3.resource("sns", region_name=REGION)

    sns.Topic(TOPIC_ARN).publish(
        Message=str(message) + END_LINE,
        Subject=subject
    )

def lambda_handler(event, context):
    # EventBridgeから渡される変数で週次(week)と月次(month)を分岐
    if "type" in event and event['type'] == "month":
        report_type = "month"
    else:
        report_type = "week"

    cur_time = datetime.now()
    if report_type == "week":
        # 基準日
        weekday = cur_time.weekday()
        # 基準日の月曜日（APIで先週のコストを取得する場合、画面設定と違ってendTimeは今週の月曜日に設定必要）
        cur_monday = cur_time - timedelta(days=weekday)
        # 基準日の先週月曜日
        last_monday = cur_time - timedelta(days=weekday + 7)
        # メールのサブジェクト用のendtime
        report_end_day = cur_time - timedelta(days=weekday + 1)
        report_end = str(report_end_day.year) + "-" + str(report_end_day.strftime('%m')) + "-" \
            + str(report_end_day.strftime('%d'))
        end = str(cur_monday.year) + "-" + str(cur_monday.strftime('%m')) + "-" \
            + str(cur_monday.strftime('%d'))
        start_member = start = str(last_monday.year) + "-" + str(last_monday.strftime('%m')) + "-" \
            + str(last_monday.strftime('%d'))
    else:
        # 基準日＞本月1日
        end = cur_time.strftime('%Y-%m-01')
        # 前月1日
        start = datetime.strftime(cur_time + relativedelta(months=-1), '%Y-%m-01')
        start_member = datetime.strftime(cur_time + relativedelta(months=-6), '%Y-%m-01')
        report_end = datetime.strftime(cur_time + relativedelta(months=-1), '%Y%m')

    # CostExplorerからデータ取得
    client = boto3.client('ce', region_name=REGION)

    # EKS全体料金
    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start,
            'End': end,
        },
        Granularity='DAILY',
        Filter={
            'Tags': {
                'Key': 'IntendedUse',
                'Values': ['eks-terrasium']
            }
        },
        Metrics=['UnblendedCost'],
        GroupBy=[{
            'Type': 'DIMENSION',
            'Key': 'SERVICE'
        }]
    )
    response_context = response_format(response)
    msg = START_LINE + "EKS全体料金" + "\n" \
        + ",".join(str(n) for n in response_context["title"]) + "\n" \
        + "\n".join(str(n) for n in response_context["output_list"]) \
        + LINE

    # EMR全体料金
    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start,
            'End': end,
        },
        Granularity='DAILY',
        Filter={
            'Tags': {
                'Key': 'IntendedUse',
                'Values': ['EMR']
            }
        },
        Metrics=['UnblendedCost'],
        GroupBy=[{
            'Type': 'DIMENSION',
            'Key': 'SERVICE'
        }]
    )
    response_context = response_format(response)
    msg += "\n" + "EMR全体料金" + "\n" \
        + ",".join(str(n) for n in response_context["title"]) + "\n" \
        + "\n".join(str(n) for n in response_context["output_list"]) \
        + LINE

    # EMR料金（CA/MA/MS/DDUチーム）-サービス別料金
    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start,
            'End': end,
        },
        Granularity='DAILY',
        Filter={
            'And': [
                {'Tags':
                    {
                        'Key': 'IntendedUse',
                        'Values': ['EMR']
                    }
                 },
                {'Tags':
                    {
                        'Key': 'Team',
                        'Values': ['CA', 'MA', 'MS', 'DDU']
                    }
                 }
            ]
        },
        Metrics=['UnblendedCost'],
        GroupBy=[{
            'Type': 'DIMENSION',
            'Key': 'SERVICE'
        }]
    )
    response_context = response_format(response)
    msg += "\n" + "EMR料金（CA/MA/MS/DDUチーム）-サービス別料金" + "\n" \
        + ",".join(str(n) for n in response_context["title"]) + "\n" \
        + "\n".join(str(n) for n in response_context["output_list"]) \
        + LINE

    # EMR料金（CA/MA/MS/DDUチーム）-P番別料金
    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start_member,
            'End': end,
        },
        Granularity='MONTHLY',
        Filter={
            'And': [
                {'Tags':
                    {
                        'Key': 'IntendedUse',
                        'Values': ['EMR']
                    }
                 },
                {'Tags':
                    {
                        'Key': 'Team',
                        'Values': ['CA', 'MA', 'MS', 'DDU']
                    }
                 }
            ]
        },
        Metrics=['UnblendedCost'],
        GroupBy=[{
            'Type': 'TAG',
            'Key': 'EmployeeNum'
        }]
    )

    response_context = response_format(response, "memberList", report_type)
    msg += "\n" + "EMR料金（CA/MA/MS/DDUチーム）-P番別料金" + "\n" \
        + ",".join(str(n) for n in response_context["title"]) + "\n" \
        + "\n".join(str(n) for n in response_context["output_list"]) \
        + LINE

    # EKS料金-P番別料金/dag-id別料金

    # 週次(week)のときは日本時間で9:00〜、月次(month)のときは10:00〜とする
    if report_type == "week":
        batch_time_start = " 00:00:00"
    else:
        batch_time_start = " 01:00:00"
    # バッチ起動標準時間
    batch_time = time.strptime(end + batch_time_start, "%Y-%m-%d %H:%M:%S")
    batch_timestamp_start = int(round(time.mktime(batch_time) * 1000))
    # バッチ予想終了時間（実行時間最大限1時間）
    batch_timestamp_end = int(round(time.mktime(batch_time) * 1000) + BATCH_EXECUTE_PERIOD)

    # EKSクラスターリストの中から、対象クラスターを抽出
    clusters = []
    cluster_list = boto3.client("eks")
    cluster_list_res = cluster_list.list_clusters()
    cluster_list_res['clusters'].sort(reverse=True)

    for val in cluster_list_res['clusters']:
        if val.startswith(os.environ['ENV'] + "-eksanalysis") and val.endswith("-cluster"):
            clusters.append(val)

    print(clusters)

    # CloudWatchLogsからCronJobログを取得
    client_log = boto3.client('logs', region_name=REGION)
    results = []

    for log_name_list in clusters:
        response = client_log.filter_log_events(
            logGroupName=log_name_list,
            logStreamNamePrefix=LOG_STREAM_NAME_PREFIX,
            startTime=batch_timestamp_start,
            endTime=batch_timestamp_end
        )
        results += response['events']

        while 'nextToken' in response.keys():
            currentToken = response['nextToken']
            response = client_log.filter_log_events(
                logGroupName=log_name_list,
                logStreamNamePrefix=LOG_STREAM_NAME_PREFIX,
                startTime=batch_timestamp_start,
                endTime=batch_timestamp_end,
                nextToken=currentToken
            )
            results += response['events']

    print(results)

    # results変数に格納されているjson形式からlogキーのみを取得
    kubecost = []

    for dict_msg in results:
        """
        dict_msg example

        {'logStreamName': 'fluentbit-kube.var.log.containers.cronjob-kubectl-cost-week-manual-w92-gbrf7_monitoring_kubectl-cost-week-eb34293c7964405683306fead57e29a8eb7c432ee308648a52bdfae29508165f.log',
        'timestamp': 1687253820158,
        'message': '{"kubernetes":{"annotations":{"kubernetes.io/psp":"eks.privileged"},
        "container_hash":"231125404608.dkr.ecr.ap-northeast-1.amazonaws.com/kubectl-cost@sha256:54603f7f42dd2ce41a9dc41ef463c13e6f2ec8cc7c301b8d378465eb04be31a3",
        "container_image":"231125404608.dkr.ecr.ap-northeast-1.amazonaws.com/kubectl-cost:v1.1",
        "container_name":"kubectl-cost-week",
        "docker_id":"eb34293c7964405683306fead57e29a8eb7c432ee308648a52bdfae29508165f",
        "host":"ip-10-3-58-21.ap-northeast-1.compute.internal",
        "labels":{"controller-uid":"32c5565e-ba0f-4f34-8643-8bb10f8034b4",
        "job-name":"cronjob-kubectl-cost-week-manual-w92"},
        "namespace_name":"monitoring",
        "pod_id":"3f2c8b32-8eca-4a34-aedf-70f7173f9721",
        "pod_name":"cronjob-kubectl-cost-week-manual-w92-gbrf7"},
        "log":"2023-06-20T09:36:54.648112064Z stdout F +-------------------------------+-----------------+------------------+"}',
        'ingestionTime': 1687253825152,
        'eventId': '37627017528590970025944144491802726703533076385874968576'}
        """

        kubecost.append(json.loads(dict_msg.get('message')).get('log'))

    """
    kubecost example

    [
    '2023-06-21T05:02:18.59015535Z stdout F +-------------------------------+-----------------+------------------+',
    '2023-06-21T05:02:18.59020021Z stdout F | CLUSTER                       | LABEL:USERNAME  | TOTAL COST (ALL) |',
    '2023-06-21T05:02:18.590204482Z stdout F +-------------------------------+-----------------+------------------+',
    '2023-06-21T05:02:18.590207371Z stdout F | dev-eksanalysis-v1-23-cluster | __unallocated__ |         6.121246 |',
    '2023-06-21T05:02:18.590210818Z stdout F |                               | p2222           |         0.015573 |',
    '2023-06-21T05:02:18.590212643Z stdout F |                               | p3333           |         0.011335 |',
    '2023-06-21T05:02:18.59021434Z stdout F |                               | p1111           |         0.011335 |',
    '2023-06-21T05:02:18.59021871Z stdout F +-------------------------------+-----------------+------------------+',
    '2023-06-21T05:02:18.590220467Z stdout F | SUMMED                        |                 |         6.159489 |',
    '2023-06-21T05:02:18.590222132Z stdout F +-------------------------------+-----------------+------------------+',
    '2023-06-21T05:02:20.321049518Z stdout F +-------------------------------+----------------------------------------+------------------+',
    '2023-06-21T05:02:20.321094144Z stdout F | CLUSTER                       | LABEL:DAG_ID                           | TOTAL COST (ALL) |',
    '2023-06-21T05:02:20.321098088Z stdout F +-------------------------------+----------------------------------------+------------------+',
    '2023-06-21T05:02:20.321100798Z stdout F | dev-eksanalysis-v1-23-cluster | __unallocated__                        |         6.159479 |',
    '2023-06-21T05:02:20.321103569Z stdout F |                               | admin_ws-lz77ci3_minoru-papermill-test |         0.000000 |',
    '2023-06-21T05:02:20.321108003Z stdout F |                               | admin_ws-sifmiac_minoru-papermill      |         0.000000 |',
    '2023-06-21T05:02:20.321110708Z stdout F +-------------------------------+----------------------------------------+------------------+',
    '2023-06-21T05:02:20.321113177Z stdout F | SUMMED                        |                                        |         6.159479 |',
    '2023-06-21T05:02:20.321115834Z stdout F +-------------------------------+----------------------------------------+------------------+'
    ]
    """

    # ログの出力は各行の先頭に"yyyy-mm-ddThh:mm:ss.sssssssssZ stdout F "の文字列がつくので、それを削除するパターンを作成
    # 小数点以下は1~9桁までで対応
    pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{1,9}Z stdout F '
    # 上記出力からテーブル形式の情報のみに整形
    split_kubecost = []
    for i in kubecost:
        table_content = re.sub(pattern, '', i)
        split_kubecost.append(table_content)
    print(split_kubecost)

    """
    split_kubecost example

    [
    ' +-------------------------------+-----------------+------------------+',
    ' | CLUSTER                       | LABEL:USERNAME  | TOTAL COST (ALL) |',
    ' +-------------------------------+-----------------+------------------+',
    ' | dev-eksanalysis-v1-23-cluster | __unallocated__ |         6.121246 |',
    ' |                               | p2222           |         0.015573 |',
    ' |                               | p3333           |         0.011335 |',
    ' |                               | p1111           |         0.011335 |',
    ' +-------------------------------+-----------------+------------------+',
    ' | SUMMED                        |                 |         6.159489 |',
    ' +-------------------------------+-----------------+------------------+',
    ' +-------------------------------+----------------------------------------+------------------+',
    ' | CLUSTER                       | LABEL:DAG_ID                           | TOTAL COST (ALL) |',
    ' +-------------------------------+----------------------------------------+------------------+',
    ' | dev-eksanalysis-v1-23-cluster | __unallocated__                        |         6.159479 |',
    ' |                               | admin_ws-lz77ci3_minoru-papermill-test |         0.000000 |',
    ' |                               | admin_ws-sifmiac_minoru-papermill      |         0.000000 |',
    ' +-------------------------------+----------------------------------------+------------------+',
    ' | SUMMED                        |                                        |         6.159479 |',
    ' +-------------------------------+----------------------------------------+------------------+'
    ]
    """

    # 上記形式から"|"が含まれている行のみに整形
    remove_separator_line = [i for i in split_kubecost if ("|" in i)]
    print(remove_separator_line)

    """
    remove_separator_line example

    [
    ' | CLUSTER                       | LABEL:USERNAME  | TOTAL COST (ALL) |',
    ' | dev-eksanalysis-v1-23-cluster | __unallocated__ |         6.121246 |',
    ' |                               | p2222           |         0.015573 |',
    ' |                               | p3333           |         0.011335 |',
    ' |                               | p1111           |         0.011335 |',
    ' | SUMMED                        |                 |         6.159489 |',
    ' | CLUSTER                       | LABEL:DAG_ID                           | TOTAL COST (ALL) |',
    ' | dev-eksanalysis-v1-23-cluster | __unallocated__                        |         6.159479 |',
    ' |                               | admin_ws-lz77ci3_minoru-papermill-test |         0.000000 |',
    ' |                               | admin_ws-sifmiac_minoru-papermill      |         0.000000 |',
    ' | SUMMED                        |                                        |         6.159479 |'
    ]
    """

    # 不要な行を削除。filter_wordsが含まれていない行を取得
    filter_words = ["CLUSTER", "__unallocated__", "SUMMED"]
    remove_needless_line = [i for i in remove_separator_line if not any(filter_word in i for filter_word in filter_words)]
    print(remove_needless_line)

    """
    remove_needless_line example

    [
    ' |                               | p2222           |         0.015573 |',
    ' |                               | p1111           |         0.011335 |',
    ' |                               | p3333           |         0.011335 |',
    ' |                               | admin_ws-lz77ci3_minoru-papermill-test |         0.000000 |',
    ' |                               | admin_ws-sifmiac_minoru-papermill      |         0.000000 |'
    ]
    """

    # 対象と料金のみに整形
    msg_list = ""
    for i in remove_needless_line:
        split = i.split("|")
        msg_list += convert_to_upper_case(split[2].strip()) + "," + split[3].strip() + "\n"
    print(msg_list)

    """
    msg_list example

    P2222,0.015573
    P3333,0.011335
    P1111,0.011335
    admin_ws-lz77ci3_minoru-papermill-test,0.000000
    admin_ws-sifmiac_minoru-papermill,0.000000
    """

    # EKS料金のメール文作成
    msg += "\n" + "EKS料金 -P番別料金/dag_id別料金" + "\n" + msg_list

    # メール件名作成
    if report_type == "week":
        subject = "週次コスト集計情報(" + start + "~" + report_end + ")"
    else:
        subject = "月次コスト集計情報(" + report_end + ")"

    # メール送信
    send_mail(subject, msg)

    return 'sendmail-success'
