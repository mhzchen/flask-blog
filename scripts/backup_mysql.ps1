# MySQL data backup: mysqldump inside container, docker cp out, keep latest N copies.
param(
    [string]$OutDir = "backups",
    [int]$Retain = 14
)
$ErrorActionPreference = "Continue"
$repo = Split-Path -Parent $PSScriptRoot
$absOut = if ([System.IO.Path]::IsPathRooted($OutDir)) { $OutDir } else { Join-Path $repo $OutDir }
New-Item -ItemType Directory -Force -Path $absOut | Out-Null
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$out = Join-Path $absOut "flask_blog_$ts.sql"
$tmp = "/tmp/flask_blog_bk.sql"

# 容器内执行 mysqldump 到临时文件，避免宿主机 pwsh 对 stderr 的 NativeCommandError
& docker exec flaskblog-db sh -c "mysqldump -uroot -proot --single-transaction --routines --triggers flask_blog > $tmp 2>/dev/null" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "mysqldump failed (exit $LASTEXITCODE)" }
& docker cp "flaskblog-db:$tmp" $out | Out-Null
& docker exec flaskblog-db rm -f $tmp | Out-Null

$item = Get-Item -LiteralPath $out
if ($item.Length -eq 0) { throw "backup file empty" }
Write-Host "backup -> $out ($($item.Length) bytes)"

Get-ChildItem -LiteralPath $absOut -Filter "flask_blog_*.sql" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip $Retain |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force }
Write-Host "retained latest $Retain backups in $absOut"