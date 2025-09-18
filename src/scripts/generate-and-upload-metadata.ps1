# Generate and upload electron-updater metadata files for GitHub releases
# This script handles the complete process of creating latest.yml and uploading it

param(
    [string]$Version = "",
    [switch]$Upload = $false,
    [switch]$Force = $false,
    [string]$Token = $env:GITHUB_TOKEN
)

# Colors for output
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Cyan = "Cyan"

function Write-ColoredOutput {
    param($Message, $Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Test-Requirements {
    Write-ColoredOutput "🔍 Checking requirements..." $Cyan
    
    # Check if gh CLI is installed
    try {
        $null = gh --version
        Write-ColoredOutput "✅ GitHub CLI (gh) is available" $Green
    }
    catch {
        Write-ColoredOutput "❌ GitHub CLI (gh) is required but not installed" $Red
        Write-ColoredOutput "Please install it from: https://cli.github.com/" $Yellow
        exit 1
    }
    
    # Check if we're in the right directory
    if (-not (Test-Path "package.json")) {
        Write-ColoredOutput "❌ package.json not found. Please run this script from the project root." $Red
        exit 1
    }
    
    # Check if Node.js is available
    try {
        $null = node --version
        Write-ColoredOutput "✅ Node.js is available" $Green
    }
    catch {
        Write-ColoredOutput "❌ Node.js is required but not found" $Red
        exit 1
    }
}

function Get-ProjectVersion {
    $packageJson = Get-Content "package.json" | ConvertFrom-Json
    return $packageJson.version
}

function Invoke-MetadataGeneration {
    param($ProjectVersion)
    
    Write-ColoredOutput "🔧 Generating metadata files for version $ProjectVersion..." $Cyan
    
    try {
        $result = node "src/scripts/generate-updater-metadata.js"
        if ($LASTEXITCODE -ne 0) {
            throw "Metadata generation failed"
        }
        Write-ColoredOutput "✅ Metadata generation completed successfully" $Green
        return $true
    }
    catch {
        Write-ColoredOutput "❌ Failed to generate metadata: $_" $Red
        return $false
    }
}

function Test-ReleaseExists {
    param($Version)
    
    try {
        $null = gh release view "v$Version" 2>$null
        return $true
    }
    catch {
        return $false
    }
}

function Invoke-MetadataUpload {
    param($ProjectVersion)
    
    $releaseTag = "v$ProjectVersion"
    
    # Check if release exists
    if (-not (Test-ReleaseExists $ProjectVersion)) {
        Write-ColoredOutput "❌ Release $releaseTag does not exist on GitHub" $Red
        Write-ColoredOutput "Please create the release first or check the version number." $Yellow
        return $false
    }
    
    # Check if latest.yml exists in project root
    if (-not (Test-Path "latest.yml")) {
        Write-ColoredOutput "❌ latest.yml not found in project root" $Red
        Write-ColoredOutput "Please run the metadata generation first." $Yellow
        return $false
    }
    
    Write-ColoredOutput "🚀 Uploading latest.yml to release $releaseTag..." $Cyan
    
    try {
        # Check if latest.yml already exists in the release
        $existingAssets = gh release view $releaseTag --json assets | ConvertFrom-Json
        $latestYmlExists = $existingAssets.assets | Where-Object { $_.name -eq "latest.yml" }
        
        if ($latestYmlExists -and -not $Force) {
            Write-ColoredOutput "⚠️  latest.yml already exists in release $releaseTag" $Yellow
            Write-ColoredOutput "Use -Force to overwrite, or delete it manually first:" $Yellow
            Write-ColoredOutput "   gh release delete-asset $releaseTag latest.yml" $Yellow
            return $false
        }
        
        if ($latestYmlExists -and $Force) {
            Write-ColoredOutput "🗑️  Removing existing latest.yml..." $Yellow
            gh release delete-asset $releaseTag latest.yml --yes
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to delete existing latest.yml"
            }
        }
        
        # Upload the new latest.yml
        gh release upload $releaseTag latest.yml
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to upload latest.yml"
        }
        
        Write-ColoredOutput "✅ Successfully uploaded latest.yml to release $releaseTag" $Green
        
        # Verify the upload
        Start-Sleep -Seconds 2
        $updatedAssets = gh release view $releaseTag --json assets | ConvertFrom-Json
        $uploadedFile = $updatedAssets.assets | Where-Object { $_.name -eq "latest.yml" }
        
        if ($uploadedFile) {
            Write-ColoredOutput "✅ Verification: latest.yml is now available in the release" $Green
            Write-ColoredOutput "📥 Download URL: $($uploadedFile.url)" $Cyan
        } else {
            Write-ColoredOutput "⚠️  Warning: Upload succeeded but verification failed" $Yellow
        }
        
        return $true
    }
    catch {
        Write-ColoredOutput "❌ Failed to upload metadata: $_" $Red
        return $false
    }
}

# Main execution
Write-ColoredOutput "🎯 Electron Updater Metadata Generator" $Cyan
Write-ColoredOutput "=====================================" $Cyan

# Test requirements
Test-Requirements

# Get version
$projectVersion = if ($Version) { $Version } else { Get-ProjectVersion }
Write-ColoredOutput "📦 Working with version: $projectVersion" $Green

# Generate metadata
$generateSuccess = Invoke-MetadataGeneration $projectVersion

if (-not $generateSuccess) {
    Write-ColoredOutput "❌ Metadata generation failed. Exiting." $Red
    exit 1
}

# Upload if requested
if ($Upload) {
    $uploadSuccess = Invoke-MetadataUpload $projectVersion
    
    if ($uploadSuccess) {
        Write-ColoredOutput "`n🎉 All done! Your auto-updater should now work." $Green
        Write-ColoredOutput "Users with version 1.0.0 should see an update notification." $Green
    } else {
        Write-ColoredOutput "`n❌ Upload failed. Please check the errors above." $Red
        exit 1
    }
} else {
    Write-ColoredOutput "`n📋 Metadata generation completed!" $Green
    Write-ColoredOutput "To upload to GitHub release, run:" $Yellow
    Write-ColoredOutput "   .\src\scripts\generate-and-upload-metadata.ps1 -Upload" $Yellow
    Write-ColoredOutput "Or manually:" $Yellow
    Write-ColoredOutput "   gh release upload v$projectVersion latest.yml" $Yellow
}

Write-ColoredOutput "`n🧪 You can test the updater by:" $Cyan
Write-ColoredOutput "1. Running your v1.0.0 app" $Cyan
Write-ColoredOutput "2. The app should detect the v$projectVersion update within 5-10 seconds" $Cyan
Write-ColoredOutput "3. Check the app logs for updater messages" $Cyan
