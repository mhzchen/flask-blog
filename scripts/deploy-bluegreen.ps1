# 蓝绿部署 / 回滚脚本（Windows PowerShell / pwsh 均可，本地可真验）
# 用法：
#   .\scripts\deploy-bluegreen.ps1            # 部署到非 active 色（就绪探针通过后切换 active）
#   .\scripts\deploy-bluegreen.ps1 -Rollback   # 回滚：切回上一 active 色
# 前提：已构建 flask-blog-backend:latest 镜像，且 flaskblog-db / flaskblog-redis 容器与
#       flask-blog_default 网络存在（docker compose up 后即满足）。
param(
  [switch]$Rollback,
  [string]$ProjectDir = (Split-Path -Parent $PSScriptRoot)
)
$ErrorActionPreference = 'Stop'
$stateFile = Join-Path $ProjectDir '.bluegreen.state'
$colors = @('blue', 'green')
$ports = @{ blue = 8001; green = 8002 }
$image = 'flask-blog-backend:latest'
$network = 'flask-blog_default'

function Get-Active {
  if (Test-Path -LiteralPath $stateFile) { (Get-Content -LiteralPath $stateFile -Raw).Trim() }
  else { 'blue' }
}
$active = Get-Active
$new = @($colors | Where-Object { $_ -ne $active })[0]
$verb = if ($Rollback) { 'rollback' } else { 'deploy' }
Write-Host "[$verb] active=$active -> target=$new (port $($ports[$new]))"

# 从 .env 读取密钥（SECRET_KEY / JWT_SECRET_KEY），未提供则回退占位值
$envMap = @{}
$envFile = Join-Path $ProjectDir '.env'
if (Test-Path -LiteralPath $envFile) {
  foreach ($line in [System.IO.File]::ReadAllLines($envFile)) {
    if ($line -match '^([^=#]+)=(.*)$') { $envMap[$matches[1]] = $matches[2] }
  }
}
$sk = if ($envMap['SECRET_KEY']) { $envMap['SECRET_KEY'] } else { 'dev-only-secret-key-not-for-prod' }
$jsk = if ($envMap['JWT_SECRET_KEY']) { $envMap['JWT_SECRET_KEY'] } else { 'dev-only-jwt-secret-not-for-prod' }

# 1) 起目标色容器（复用 backend 镜像 + 现有 db/redis 网络，端口 8001/8002）
docker rm -f "flaskblog-backend-$new" 2>$null | Out-Null
docker run -d --name "flaskblog-backend-$new" --network $network -p "$($ports[$new]):8000" `
  -e "DATABASE_URL=mysql+pymysql://root:root@db:3306/flask_blog?charset=utf8mb4" `
  -e "SECRET_KEY=$sk" -e "JWT_SECRET_KEY=$jsk" `
  -e "FLASK_ENV=production" -e "CORS_ORIGINS=http://localhost:8080" `
  -e "CACHE_ENABLED=true" -e "CACHE_REDIS_URL=redis://redis:6379/0" `
  -e "CELERY_BROKER_URL=redis://redis:6379/1" -e "CELERY_RESULT_BACKEND=redis://redis:6379/1" `
  -e "RATELIMIT_STORAGE_URI=redis://redis:6379/2" `
  $image *> "C:\Windows\Temp\bluegreen-run.txt" 2>&1
if ($LASTEXITCODE -ne 0) { throw "docker run failed: $(Get-Content 'C:\Windows\Temp\bluegreen-run.txt' -Raw)" }

# 2) 就绪探针：轮询 /health 直到 ok（最多 60s），未通过则下线该色并保持旧 active
$health = "http://localhost:$($ports[$new])/health"
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
  try { $r = Invoke-RestMethod $health -TimeoutSec 2; if ($r.status -eq 'ok') { $ok = $true; break } }
  catch { Start-Sleep 2 }
}
if (-not $ok) {
  docker rm -f "flaskblog-backend-$new" 2>$null | Out-Null
  throw "blue-green $new readiness probe failed; kept active=$active"
}

# 3) 切换 active 标记 + 停掉旧 active 容器（回滚后旧色即另一色）
Set-Content -LiteralPath $stateFile -Value $new -Encoding ascii
docker rm -f "flaskblog-backend-$active" 2>$null | Out-Null
Write-Host "blue-green[$verb] done: active=$new (port $($ports[$new])), old $active down. health: $health"