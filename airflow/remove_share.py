from datetime import timedelta
import pendulum
from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.bash import BashOperator
from terrasium.airflow.operators.workspace import (
    GetTerrasiumWorkspaceOperator,
    TerrasiumWorkspaceOperator,
)

# Change to your workspace ID
WORKSPACE_ID = "ws-xxx"
UNIT_NAME = "xxd_xxu"  # ユニット名を次から選択してください。"cad_dtu", "cad_dtu", "cad_emu", "cad_mau", "cad_vdu", "msd_edu", "msd_psu"
DAG_NAME = "remove-under-share"  # Airflowの用途
START_DATE = "2022/8/3"  # ジョブの開始日
SCHEDULE_INTERVAL = "0 9 * * *"  # ジョブの実行スケジュール(cron形式) タイムゾーンはJST(日本時間)となっています
RESOURCES_SIZE = "S"  # Executer実行の際にリクエストするリソースサイズ 下記RESOURCES_CONFIGを参照し、S,M,Lから選択してください

# Resource 編集しないでください
RESOURCES_CONFIG = {
    "S": {
        "request_cpu": "0.5",
        "request_memory": "1Gi",
        "limit_cpu": "3.0",
        "limit_memory": "22Gi",
    },
    "M": {
        "request_cpu": "0.5",
        "request_memory": "1Gi",
        "limit_cpu": "4.0",
        "limit_memory": "28Gi",
    },
    "L": {
        "request_cpu": "0.5",
        "request_memory": "1Gi",
        "limit_cpu": "5.0",
        "limit_memory": "36Gi",
    },
}
RESOURCES = RESOURCES_CONFIG[RESOURCES_SIZE]


BASE_DIR = "/home/terrasium/sample_code"
EXECUTION_DATE = (
    '{{ execution_date.in_timezone("Asia/Tokyo").format("YYYYMMDD-hh:mm:ssZ") }}'  # noqa: E501
)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["airflow@example.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(seconds=10),
}


with DAG(
    UNIT_NAME + "_" + WORKSPACE_ID + "_" + DAG_NAME,
    default_args=default_args,
    description="remove share under share",
    start_date=pendulum.datetime(
        int(START_DATE.split("/")[0]),
        int(START_DATE.split("/")[1]),
        int(START_DATE.split("/")[2]),
        tz="Asia/Tokyo",
    ),
    schedule_interval=SCHEDULE_INTERVAL,
    tags=[UNIT_NAME],
    catchup=False,
) as dag:
    spec = GetTerrasiumWorkspaceOperator(
        task_id="spec",
        workspace_id=WORKSPACE_ID,
        # Kubernetes PodのRBACを使用
        in_cluster=True,
    )

    rm = TerrasiumWorkspaceOperator(
        task_id="remove-share-under-share",
        name="remove-share-under-share",
        workspace_id=WORKSPACE_ID,
        # imageを指定しない場合はTerrasiumと同じバージョンのJupyterLabイメージを使用
        arguments=[
            "/bin/bash",
            "-c",
            "rm -rf /home/terrasium/share/share",
        ],
        container_resources=RESOURCES,
    )

    spec >> rm
