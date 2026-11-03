# 监控栈一键启用 + 验证清单（#43）
# 前置：Docker Hub 网络可达（能拉取 prometheus/grafana/otel-collector 镜像）。
# 用法：powershell -File scripts\monitoring-up.ps1
$ErrorActionPreference = 'Stop'
Write-Host "[monitoring] 拉起 prometheus / grafana / otel-collector ..."
docker compose up -d prometheus grafana otel-collector
Start-Sleep 8
Write-Host ""
Write-Host "========== 监控栈验证清单 =========="
Write-Host "1) Grafana 面板: http://localhost:3000  (admin/admin)"
Write-Host "   -> Data Sources 已含 Prometheus，打开 'Flask Overview' 面板（uid=flask-overview，7 面板）"
Write-Host "2) Prometheus 抓取: http://localhost:9090/targets"
Write-Host "   -> backend / worker / beat 全部 UP；确认 /api/metrics 被抓取（http_srv 目标）"
Write-Host "3) 告警规则: http://localhost:9090/alerts"
Write-Host "   -> FlaskBackendDown / FlaskHighErrorRate 规则已加载"
Write-Host "   触发验证：docker stop flaskblog-backend 后告警应进入 firing，再 start 恢复"
Write-Host "4) 链路采集: backend 已配 OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318"
Write-Host "   -> 请求若干接口后，span 经 collector 落盘 monitoring/traces/traces.json"
Write-Host "   查看瀑布：venv\Scripts\python scripts\trace_report.py  -> reports/trace-report.html"
Write-Host "5) 容器状态：docker compose ps 应见 flaskblog-prometheus / -grafana / -otel-collector 为 Up"
Write-Host ""
docker compose ps --filter "name=flaskblog-prometheus" --filter "name=flaskblog-grafana" --filter "name=flaskblog-otel-collector" --format "{{.Name}}: {{.Status}}"