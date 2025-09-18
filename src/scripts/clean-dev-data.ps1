# Clean Development Data Script
# This script removes all development vector databases, caches, and temporary files
# to ensure a clean production build without personal data.
#
# Usage: Run this script before building/packaging the app
# .\src\scripts\clean-dev-data.ps1

param(
    [switch]$Verbose = $false,
    [switch]$WhatIf = $false
)

Write-Host "🧹 SIFFS Development Data Cleanup Script" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Track total cleaned size
$totalCleaned = 0

# Function to remove directory with size calculation
function Remove-DirectoryWithStats {
    param(
        [string]$Path,
        [string]$Description
    )
    
    if (Test-Path $Path) {
        try {
            # Calculate size before removal
            $size = (Get-ChildItem $Path -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
            if ($null -eq $size) { $size = 0 }
            $sizeMB = [math]::Round($size / 1048576, 2)
            
            if ($WhatIf) {
                Write-Host "WHAT-IF: Would remove $Description" -ForegroundColor Yellow
                Write-Host "  Path: $Path" -ForegroundColor Gray
                Write-Host ('  Size: ' + $sizeMB + ' MB') -ForegroundColor Gray
            } else {
                Write-Host "🗑️  Removing $Description..." -ForegroundColor Yellow
                Write-Host "   Path: $Path" -ForegroundColor Gray
                Write-Host ('   Size: ' + $sizeMB + ' MB') -ForegroundColor Gray
                
                Remove-Item $Path -Recurse -Force -ErrorAction SilentlyContinue
                
                if (-not (Test-Path $Path)) {
                    Write-Host "   ✅ Successfully removed" -ForegroundColor Green
                    $script:totalCleaned += $sizeMB
                } else {
                    Write-Host "   ❌ Failed to remove" -ForegroundColor Red
                }
            }
        } catch {
            Write-Host "   ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        if ($Verbose) {
            Write-Host "   ℹ️  Not found: $Path" -ForegroundColor Gray
        }
    }
    Write-Host ""
}

# Function to clean temp directories matching pattern
function Clean-TempDirectories {
    param(
        [string]$Pattern,
        [string]$Description
    )
    
    Write-Host "🧹 Cleaning $Description..." -ForegroundColor Yellow
    
    try {
        $tempDirs = Get-ChildItem -Path $env:TEMP -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match $Pattern }
        $cleanedCount = 0
        $cleanedSize = 0
        
        foreach ($dir in $tempDirs) {
            try {
                $size = (Get-ChildItem $dir.FullName -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
                if ($null -eq $size) { $size = 0 }
                $sizeMB = [math]::Round($size / 1048576, 2)
                
                if ($WhatIf) {
                    Write-Host ('   WHAT-IF: Would remove ' + $dir.Name + ' (' + $sizeMB + ' MB)') -ForegroundColor Yellow
                } else {
                    if ($Verbose) {
                        Write-Host ('   Removing: ' + $dir.Name + ' (' + $sizeMB + ' MB)') -ForegroundColor Gray
                    }
                    Remove-Item $dir.FullName -Recurse -Force -ErrorAction SilentlyContinue
                    $cleanedCount++
                    $cleanedSize += $size
                }
            } catch {
                if ($Verbose) {
                    Write-Host "   ❌ Error removing $($dir.Name): $($_.Exception.Message)" -ForegroundColor Red
                }
            }
        }
        
        if ($WhatIf) {
            Write-Host "   WHAT-IF: Would clean $($tempDirs.Count) directories" -ForegroundColor Yellow
        } else {
            $sizeMB = [math]::Round($cleanedSize / 1048576, 2)
            Write-Host ('   ✅ Cleaned ' + $cleanedCount + ' directories (' + $sizeMB + ' MB)') -ForegroundColor Green
            $script:totalCleaned += $sizeMB
        }
    } catch {
        Write-Host "   ❌ Error cleaning temp directories: $($_.Exception.Message)" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "Starting cleanup process..." -ForegroundColor White
Write-Host ""

# 1. Clean Qdrant Vector Databases
Write-Host "📊 Cleaning Vector Databases" -ForegroundColor Cyan
Write-Host "----------------------------" -ForegroundColor Cyan

# Windows AppData locations
Remove-DirectoryWithStats -Path "$env:LOCALAPPDATA\SIFFS" -Description "Local AppData SIFFS database"
Remove-DirectoryWithStats -Path "$env:APPDATA\SIFFS" -Description "Roaming AppData SIFFS database"

# Alternative locations (Mac/Linux style paths that might exist)
Remove-DirectoryWithStats -Path "$env:USERPROFILE\.local\share\SIFFS" -Description "Unix-style SIFFS database"

# Project directory databases (if any)
Remove-DirectoryWithStats -Path ".\vector_db" -Description "Project vector database"
Remove-DirectoryWithStats -Path ".\qdrant_data" -Description "Project Qdrant data"

# 2. Clean Temporary Slide Caches
Write-Host "🖼️  Cleaning Temporary Slide Caches" -ForegroundColor Cyan
Write-Host "------------------------------------" -ForegroundColor Cyan

Clean-TempDirectories -Pattern "pptx_slides_.*" -Description "PowerPoint slide cache directories"
Clean-TempDirectories -Pattern "siffs.*" -Description "SIFFS temporary directories"

# 3. Clean Python Cache and Build Artifacts
Write-Host "🐍 Cleaning Python Artifacts" -ForegroundColor Cyan
Write-Host "-----------------------------" -ForegroundColor Cyan

Remove-DirectoryWithStats -Path ".\build" -Description "Python build artifacts"
Remove-DirectoryWithStats -Path ".\resources" -Description "Python resources (will be rebuilt)"

# Find and remove __pycache__ directories
Write-Host "🧹 Cleaning Python cache directories..." -ForegroundColor Yellow
try {
    $pycachedirs = Get-ChildItem -Path ".\src\python-server" -Recurse -Directory -Name "__pycache__" -ErrorAction SilentlyContinue
    $cleanedPyCache = 0
    
    foreach ($dir in $pycachedirs) {
        $fullPath = Join-Path ".\src\python-server" $dir
        if ($WhatIf) {
            Write-Host "   WHAT-IF: Would remove $fullPath" -ForegroundColor Yellow
        } else {
            if ($Verbose) {
                Write-Host "   Removing: $fullPath" -ForegroundColor Gray
            }
            Remove-Item $fullPath -Recurse -Force -ErrorAction SilentlyContinue
            $cleanedPyCache++
        }
    }
    
    if ($WhatIf) {
        Write-Host "   WHAT-IF: Would clean $($pycachedirs.Count) __pycache__ directories" -ForegroundColor Yellow
    } else {
        Write-Host "   ✅ Cleaned $cleanedPyCache __pycache__ directories" -ForegroundColor Green
    }
} catch {
    Write-Host "   ❌ Error cleaning __pycache__: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# 4. Clean Node.js Build Artifacts (optional)
Write-Host "📦 Cleaning Node.js Artifacts" -ForegroundColor Cyan
Write-Host "------------------------------" -ForegroundColor Cyan

Remove-DirectoryWithStats -Path ".\.webpack" -Description "Webpack build cache"
Remove-DirectoryWithStats -Path ".\out" -Description "Electron Forge output"

# 5. Summary
Write-Host "📋 Cleanup Summary" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan

if ($WhatIf) {
    Write-Host "🔍 WHAT-IF MODE: No files were actually removed" -ForegroundColor Yellow
    Write-Host "   Run without -WhatIf to perform actual cleanup" -ForegroundColor Gray
} else {
    Write-Host "✅ Total data cleaned: $totalCleaned MB" -ForegroundColor Green
    Write-Host "🎉 Development data cleanup completed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "💡 Your production build will now be clean of personal development data." -ForegroundColor Blue
    Write-Host "   Users will start with empty databases and populate them with their own files." -ForegroundColor Blue
}

Write-Host ""
Write-Host "🚀 Ready for clean production build!" -ForegroundColor Magenta
