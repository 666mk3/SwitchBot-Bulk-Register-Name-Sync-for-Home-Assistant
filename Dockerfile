FROM python:3.12-alpine

# キャッシュを強制的に無効化するための環境変数 (v1.1.5)
ENV REFRESHED_AT 2026-01-16

# 必要なライブラリのインストール
RUN pip install --no-cache-dir requests websockets

# スクリプトのコピー
COPY sync.py /
RUN chmod a+x /sync.py

# 直接実行
CMD [ "python", "/sync.py" ]
