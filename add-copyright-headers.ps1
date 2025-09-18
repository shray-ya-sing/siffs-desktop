# PowerShell script to add GPL copyright headers to source code files
# Usage: .\add-copyright-headers.ps1

param(
    [switch]$WhatIf = $false,
    [string]$Author = "Siffs",
    [string]$Email = "github.suggest277@passinbox.com",
    [int]$Year = 2025
)

# Copyright header templates for different file types
$Templates = @{
    # TypeScript/JavaScript files (.ts, .tsx, .js, .jsx)
    "ts" = @"
/*
 * Siffs - Fast File Search Desktop Application
 * Copyright (C) $Year  $Author
 * 
 * Contact: $Email
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

"@

    # Python files (.py)
    "py" = @"
# Siffs - Fast File Search Desktop Application
# Copyright (C) $Year  $Author
# 
# Contact: $Email
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"@
}

# File extensions to process
$FileExtensions = @{
    "*.ts"  = "ts"
    "*.tsx" = "ts" 
    "*.js"  = "ts"
    "*.jsx" = "ts"
    "*.py"  = "py"
}

# Files to exclude (add patterns here)
$ExcludePatterns = @(
    "*node_modules*",
    "*\.git*",
    "*dist*",
    "*build*",
    "*out*",
    "*\.webpack*",
    "*__pycache__*",
    "*venv*",
    "*site-packages*",
    "*tests*",
    "*.min.js",
    "package-lock.json"
)

function Test-ShouldExclude {
    param([string]$FilePath)
    
    foreach ($pattern in $ExcludePatterns) {
        if ($FilePath -like $pattern) {
            return $true
        }
    }
    return $false
}

function Test-HasCopyright {
    param([string]$FilePath)
    
    $content = Get-Content $FilePath -Raw -ErrorAction SilentlyContinue
    if (-not $content) { return $false }
    
    # Check if file already has copyright notice
    return ($content -match "Copyright.*$Author" -or 
            $content -match "GNU General Public License" -or
            $content -match "This program is free software")
}

function Add-CopyrightHeader {
    param(
        [string]$FilePath,
        [string]$Template
    )
    
    if (Test-ShouldExclude $FilePath) {
        Write-Host "⏭️  Skipping excluded file: $FilePath" -ForegroundColor Yellow
        return
    }
    
    if (Test-HasCopyright $FilePath) {
        Write-Host "✅ Already has copyright: $FilePath" -ForegroundColor Green
        return
    }
    
    if ($WhatIf) {
        Write-Host "🔍 Would add copyright to: $FilePath" -ForegroundColor Cyan
        return
    }
    
    try {
        $existingContent = Get-Content $FilePath -Raw -ErrorAction SilentlyContinue
        if (-not $existingContent) {
            $existingContent = ""
        }
        
        # Combine header with existing content
        $newContent = $Template + $existingContent
        
        # Write back to file
        Set-Content $FilePath $newContent -Encoding UTF8 -NoNewline
        Write-Host "✨ Added copyright to: $FilePath" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Error processing $FilePath : $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Main execution
Write-Host "🔍 Scanning for source files..." -ForegroundColor Cyan
Write-Host "Author: $Author" -ForegroundColor Gray
Write-Host "Email: $Email" -ForegroundColor Gray
Write-Host "Year: $Year" -ForegroundColor Gray

if ($WhatIf) {
    Write-Host "🚀 DRY RUN MODE - No files will be modified" -ForegroundColor Yellow
}

$processedCount = 0
$skippedCount = 0
$errorCount = 0

# Process each file type
foreach ($extension in $FileExtensions.Keys) {
    $templateType = $FileExtensions[$extension]
    $template = $Templates[$templateType]
    
    Write-Host "`n📁 Processing $extension files..." -ForegroundColor Cyan
    
    $files = Get-ChildItem -Path "src" -Filter $extension -Recurse -File
    
    foreach ($file in $files) {
        if (Test-ShouldExclude $file.FullName) {
            $skippedCount++
            continue
        }
        
        Add-CopyrightHeader -FilePath $file.FullName -Template $template
        $processedCount++
    }
}

# Summary
Write-Host "`n📊 Summary:" -ForegroundColor Cyan
Write-Host "Processed: $processedCount files" -ForegroundColor Green
Write-Host "Skipped: $skippedCount files" -ForegroundColor Yellow

if ($WhatIf) {
    Write-Host "`n💡 Run without -WhatIf to actually add headers" -ForegroundColor Yellow
}
else {
    Write-Host "`n🎉 Copyright headers have been added!" -ForegroundColor Green
    Write-Host "📋 Your source files are now protected under GPL-3.0" -ForegroundColor Green
}
