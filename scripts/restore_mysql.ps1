# MySQL data restore: import backup sql into database (drill).
param(
    [Parameter(Mandatory = $true)][string]$BackupFile,
    [string]$Database = "flask_blog"
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $BackupFile)) { throw "backup file not found: $BackupFile" }
Get-Content -LiteralPath $BackupFile -Raw -Encoding utf8 |
    docker exec -i flaskblog-db sh -c "exec mysql -uroot -proot $Database" 2>&1
Write-Host "restored: $BackupFile -> $Database"