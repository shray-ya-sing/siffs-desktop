# Clean Build Script
# This script performs a complete cleanup of development data and then builds the production app
#
# Usage: 
# .\src\scripts\clean-build.ps1                    # Clean build with make
# .\src\scripts\clean-build.ps1 -Publish          # Clean build with publish
# .\src\scripts\clean-build.ps1 -Package          # Clean build with package only

param(
    [switch]$Publish = $false,
    [switch]$Package = $false,
    [switch]$Verbose = $false,
    [switch]$WhatIf = $false
)

Write-Host "🏗️ SIFFS Clean Build Script" -ForegroundColor Magenta
Write-Host "============================" -ForegroundColor Magenta
Write-Host ""

# Determine build type
$buildType = "make"
if ($Publish) {
    $buildType = "publish"
} elseif ($Package) {
    $buildType = "package"
}

Write-Host "📋 Build Configuration:" -ForegroundColor Cyan
Write-Host "   Build Type: $buildType" -ForegroundColor White
Write-Host "   Verbose: $Verbose" -ForegroundColor White
Write-Host "   What-If: $WhatIf" -ForegroundColor White
Write-Host ""

if ($WhatIf) {
    Write-Host "🔍 WHAT-IF MODE: No actual changes will be made" -ForegroundColor Yellow
    Write-Host ""
}

# Step 1: Clean development data
Write-Host "🧹 Step 1: Cleaning development data..." -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Yellow

$cleanArgs = @()
if ($Verbose) { $cleanArgs += "-Verbose" }
if ($WhatIf) { $cleanArgs += "-WhatIf" }

try {
    $cleanScriptPath = ".\src\scripts\clean-dev-data.ps1"
    if (Test-Path $cleanScriptPath) {
        & $cleanScriptPath @cleanArgs
        if ($LASTEXITCODE -eq 0 -or $null -eq $LASTEXITCODE) {
            Write-Host "✅ Development data cleanup completed" -ForegroundColor Green
        } else {
            Write-Host "❌ Development data cleanup failed with exit code: $LASTEXITCODE" -ForegroundColor Red
            exit $LASTEXITCODE
        }
    } else {
        Write-Host "❌ Clean script not found: $cleanScriptPath" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Error during cleanup: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Build the application
if (-not $WhatIf) {
    Write-Host "🏗️ Step 2: Building application..." -ForegroundColor Yellow
    Write-Host "===================================" -ForegroundColor Yellow
    
    $buildCommand = switch ($buildType) {
        "publish" { "npm run publish" }
        "package" { "npm run package" }
        "make" { "npm run make" }
    }
    
    Write-Host "Running: $buildCommand" -ForegroundColor White
    Write-Host ""
    
    try {
        Invoke-Expression $buildCommand
        if ($LASTEXITCODE -eq 0 -or $null -eq $LASTEXITCODE) {
            Write-Host ""
            Write-Host "🎉 Build completed successfully!" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "❌ Build failed with exit code: $LASTEXITCODE" -ForegroundColor Red
            exit $LASTEXITCODE
        }
    } catch {
        Write-Host "❌ Error during build: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "🔍 Step 2: WHAT-IF - Would build application with: npm run $buildType" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🚀 Clean Build Process Complete!" -ForegroundColor Magenta
Write-Host ""

if (-not $WhatIf) {
    Write-Host "💡 Your application has been built with clean production data:" -ForegroundColor Blue
    Write-Host "   ✅ No personal development files included" -ForegroundColor Blue  
    Write-Host "   ✅ Users will start with fresh, empty databases" -ForegroundColor Blue
    Write-Host "   ✅ Ready for distribution" -ForegroundColor Blue
}
