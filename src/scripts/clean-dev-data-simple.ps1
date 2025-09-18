# Simple Development Data Cleanup Script
# Removes Qdrant vector store data to prevent dev data from being bundled

param(
    [switch]$WhatIf = $false
)

Write-Host "Cleaning development vector store data..." -ForegroundColor Cyan

# Paths where Qdrant vector data might be stored
$paths = @(
    "$env:LOCALAPPDATA\SIFFS",
    "$env:APPDATA\SIFFS", 
    "$env:USERPROFILE\.local\share\SIFFS",
    ".\vector_db",
    ".\qdrant_data",
    ".\qdrant_storage"
)

$removedCount = 0

foreach ($path in $paths) {
    if (Test-Path $path) {
        if ($WhatIf) {
            Write-Host "WHAT-IF: Would remove $path" -ForegroundColor Yellow
        } else {
            try {
                Remove-Item $path -Recurse -Force -ErrorAction Stop
                Write-Host "Removed: $path" -ForegroundColor Green
                $removedCount++
            } catch {
                Write-Host "Failed to remove: $path - $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "Not found: $path" -ForegroundColor Gray
    }
}

if ($WhatIf) {
    Write-Host "WHAT-IF: Would attempt to clean vector store data" -ForegroundColor Yellow
} else {
    Write-Host "Cleanup complete. Removed $removedCount directories." -ForegroundColor Green
    Write-Host "Ready for clean production build!" -ForegroundColor Magenta
}
