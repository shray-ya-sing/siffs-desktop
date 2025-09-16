// Build script to create a single-file Python executable for SIFFS server
//
// Usage: node build-py.js
// IMPORTANT NOTE: always run this script from the ROOT directory of the project, otherwise path resolution will fail and the script will not run successfully
// 
// This script will build a single-file Python executable for the SIFFS server
// containing only the essential packages: FastAPI, VoyageAI, Pinecone, PyWin32, and Pillow.
// The executable will be placed in the resources directory.
// The script will clean up existing build and dist directories if they exist
//
// Dependencies: 
// - cross-spawn
// - path
// - fs-extra
// - os
const spawn = require('cross-spawn');
const path = require('path');
const fs = require('fs-extra');
const os = require('os');

function buildPython() {
    console.log('Building Python executable...');

    const rootDir = process.cwd();    
    const pythonDir = path.join(rootDir, 'src', 'python-server');
    const buildDir = path.join(rootDir, 'build', 'python');
    const distDir = path.join(rootDir, 'resources', 'python');

    // Clean up existing build and dist directories if they exist -- or name them, if they do not
    [buildDir, distDir].forEach(dir => {
        const dirPath = path.dirname(dir);
        if (fs.existsSync(dirPath)) {
            console.log(`Cleaning up ${dir}...`);
            try {
                fs.removeSync(dir);
                console.log(`Successfully removed ${dir}`);
                // Create the directory again
                fs.mkdirSync(dirPath, { recursive: true });
            } catch (error) {
                console.error(`Failed to remove ${dir}:`, error.message);
                process.exit(1);
            }
        }
        else {
            fs.mkdirSync(dirPath, { recursive: true });
        }
    });
    
    // PyInstaller command
    const pyInstallerArgs = [
        //'--noconsole',
        '--noconfirm',
        '--distpath', distDir,
        '--workpath', buildDir,
        '--specpath', buildDir,
        // Hooks
        '--additional-hooks-dir', pythonDir,
        '--runtime-hook', path.join(pythonDir, 'runtime-hook-encoding.py'),
        // Add essential hidden imports for SIFFS
        '--hidden-import=python_dotenv',
        '--hidden-import=uvicorn',
        '--hidden-import=fastapi',
        '--hidden-import=pydantic',
        '--hidden-import=starlette',
        '--hidden-import=voyageai',
        '--hidden-import=pinecone',
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=win32com.client',
        '--hidden-import=pythoncom',
        // Copy metadata for essential SIFFS packages
        '--copy-metadata', 'fastapi',
        '--copy-metadata', 'uvicorn',
        '--copy-metadata', 'pydantic',
        '--copy-metadata', 'starlette',
        '--copy-metadata', 'voyageai',
        '--copy-metadata', 'pinecone',
        '--copy-metadata', 'pillow',
        '--copy-metadata', 'python-dotenv',
        '--copy-metadata', 'pywin32',
        // Add the python-server directory to the path
        '--paths', pythonDir,
        // Collect essential SIFFS components
        '--collect-all', 'fastapi',
        '--collect-all', 'uvicorn',
        '--collect-all', 'pydantic',
        '--collect-all', 'pydantic_core',
        '--collect-all', 'starlette',
        '--collect-all', 'anyio',
        '--collect-all', 'voyageai',
        '--collect-all', 'pinecone',
        '--collect-all', 'PIL',
        '--collect-all', 'python_dotenv',
        // Name of the main python server dir
        '--name=python-server',        
        // Add SIFFS Python files and directories
        '--add-data', `${path.join(pythonDir, 'app.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, 'asgi.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, '__init__.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, 'logging_config.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, '*.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, 'api')}${path.delimiter}api`,
        '--add-data', `${path.join(pythonDir, 'services')}${path.delimiter}services`,
        // Entry point for prod server
        '--onedir',
        path.join(pythonDir, 'asgi.py')
    ];

    console.log('Running: pyinstaller', pyInstallerArgs.join(' '));
    
    // Execute build
    const result = spawn.sync('pyinstaller', pyInstallerArgs, {
        cwd: rootDir,
        stdio: 'inherit'
    });

    if (result.status !== 0) {
        console.error('Python build failed');
        process.exit(1);
    }

    console.log('Python build successful');
    
    // Ensure resources directory exists
    const resourcesDir = path.join(__dirname, '../../resources');
    if (!fs.existsSync(resourcesDir)) {
        fs.mkdirSync(resourcesDir, { recursive: true });
    }

    // Copy asgi.py to resources (main entry point for SIFFS)
    const asgiSource = path.join(__dirname, '../python-server/asgi.py');
    const asgiDest = path.join(__dirname, '../../resources/asgi.py');
    fs.copyFileSync(asgiSource, asgiDest);
    console.log(`Copied asgi.py to ${asgiDest}`);

    // Copy the env file to the package resources
    // Update the .env copy section to be non-blocking
    const envSource = path.join(__dirname, '../../.env');
    const envDest = path.join(distDir, '.env');

    try {
        if (fs.existsSync(envSource)) {
            fs.copyFileSync(envSource, envDest);
            console.log(`Copied .env to ${envDest}`);
        } else {
            console.log('No .env file found to copy');
        }
    } catch (error) {
        console.warn('Could not copy .env file:', error.message);
    }

    return true;
}

module.exports = { buildPython };

// Run if called directly
if (require.main === module) {
    buildPython();    
}
