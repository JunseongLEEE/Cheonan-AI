#!/usr/bin/env bash
# 앱 헬스 보장 후 페르소나 캡처 (앱 죽으면 재기동)
cd /root/Cheonan-AI
if ! curl -s -o /dev/null --max-time 4 http://localhost:8501; then
  nohup setsid /root/venvs/app/bin/python -m streamlit run app.py \
    --server.port 8501 --server.address 0.0.0.0 --server.headless true \
    > logs/streamlit.log 2>&1 &
  for i in $(seq 1 20); do
    curl -s -o /dev/null --max-time 3 http://localhost:8501 && break
    sleep 2
  done
  sleep 4
fi
/root/venvs/app/bin/python scripts/eval_agent/persona_capture.py
