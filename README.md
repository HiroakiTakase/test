# raizin-policy-collection
RAIZINのIAM以外のリソースポリシーを取得するコード

通常のポリシー変更プロセスでは本レポジトリは用いない。

コードの変更が発生した場合のみ本レポジトリを用いてコードレビューを行い、
問題ないことを確認した後にBacklogGit(https://aws-plus.backlog.jp/git/KDDI_RAIZIN_DEV/raizin-policy-collection/tree/master )へプッシュする流れを想定している。


機能改修時に商用、開発環境のjsonファイルが必要な場合、Backlog Git にあるjsonデータを正としてローカルで取り込み検証する。
Push時には取り込んだjsonデータは削除して本Git環境のリポジトリにはプッシュしないこと。
