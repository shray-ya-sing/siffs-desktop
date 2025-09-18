const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');

/**
 * Generate metadata files required by electron-updater for GitHub releases
 * This script creates latest.yml and other necessary files for auto-updates
 */

function calculateSha512(filePath) {
  const fileBuffer = fs.readFileSync(filePath);
  const hash = crypto.createHash('sha512');
  hash.update(fileBuffer);
  return hash.digest('base64');
}

function getFileSize(filePath) {
  const stats = fs.statSync(filePath);
  return stats.size;
}

function generateLatestYml(version, setupExePath, nupkgPath) {
  // Calculate checksums and sizes
  const setupSha512 = calculateSha512(setupExePath);
  const setupSize = getFileSize(setupExePath);
  const nupkgSha512 = calculateSha512(nupkgPath);
  const nupkgSize = getFileSize(nupkgPath);
  
  // Get just the filename without path
  const setupFileName = path.basename(setupExePath);
  const nupkgFileName = path.basename(nupkgPath);
  
  const latestYml = `version: ${version}
files:
  - url: ${setupFileName}
    sha512: ${setupSha512}
    size: ${setupSize}
    blockMapSize: 0
  - url: ${nupkgFileName}
    sha512: ${nupkgSha512}
    size: ${nupkgSize}
path: ${setupFileName}
sha512: ${setupSha512}
releaseDate: ${new Date().toISOString()}`;

  return latestYml;
}

function main() {
  try {
    // Get version from package.json
    const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
    const version = packageJson.version;
    
    console.log(`📦 Generating metadata for version ${version}`);
    
    // Find the built files in the out directory
    const outDir = path.join(__dirname, '../../out');
    
    if (!fs.existsSync(outDir)) {
      console.error('❌ Output directory not found. Please run "npm run make" first.');
      process.exit(1);
    }
    
    // Look for the setup.exe and .nupkg files
    let setupExePath = null;
    let nupkgPath = null;
    
    // Search for files recursively in out directory
    function findFiles(dir) {
      const files = fs.readdirSync(dir);
      for (const file of files) {
        const filePath = path.join(dir, file);
        const stat = fs.statSync(filePath);
        
        if (stat.isDirectory()) {
          findFiles(filePath);
        } else if (file.endsWith('Setup.exe')) {
          setupExePath = filePath;
          console.log(`✅ Found Setup.exe: ${filePath}`);
        } else if (file.endsWith('full.nupkg')) {
          nupkgPath = filePath;
          console.log(`✅ Found .nupkg: ${filePath}`);
        }
      }
    }
    
    findFiles(outDir);
    
    if (!setupExePath || !nupkgPath) {
      console.error('❌ Could not find required files. Looking for:');
      console.error('  - *Setup.exe file');
      console.error('  - *full.nupkg file');
      console.error('\nPlease ensure you have run "npm run make" successfully.');
      process.exit(1);
    }
    
    // Generate latest.yml content
    console.log('🔧 Generating latest.yml...');
    const latestYmlContent = generateLatestYml(version, setupExePath, nupkgPath);
    
    // Write latest.yml to the same directory as the build files
    const outputDir = path.dirname(setupExePath);
    const latestYmlPath = path.join(outputDir, 'latest.yml');
    
    fs.writeFileSync(latestYmlPath, latestYmlContent);
    console.log(`✅ Generated latest.yml at: ${latestYmlPath}`);
    
    console.log('\n📄 Generated latest.yml content:');
    console.log('─'.repeat(50));
    console.log(latestYmlContent);
    console.log('─'.repeat(50));
    
    // Also create a copy in the project root for easy upload
    const rootLatestYml = path.join(__dirname, '../../latest.yml');
    fs.writeFileSync(rootLatestYml, latestYmlContent);
    console.log(`✅ Also created copy at project root: ${rootLatestYml}`);
    
    console.log('\n🚀 Next steps:');
    console.log('1. Upload latest.yml to your GitHub release:');
    console.log(`   gh release upload v${version} "${latestYmlPath}"`);
    console.log(`   - OR - `);
    console.log(`   gh release upload v${version} latest.yml`);
    console.log('');
    console.log('2. Your auto-updater should now detect the update!');
    
    return {
      version,
      latestYmlPath,
      setupExePath,
      nupkgPath
    };
    
  } catch (error) {
    console.error('❌ Error generating metadata:', error);
    process.exit(1);
  }
}

// Export for use as module or run directly
if (require.main === module) {
  main();
} else {
  module.exports = { main, generateLatestYml, calculateSha512, getFileSize };
}
