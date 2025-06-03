// scripts/build-python.js
const spawn = require('cross-spawn');
const path = require('path');
const fs = require('fs-extra');
const os = require('os');

function buildPython() {
    console.log('🔨 Building Python executable...');

    const rootDir = process.cwd();    
    const pythonDir = path.join(rootDir, 'src', 'python-server');
    const buildDir = path.join(rootDir, 'build', 'python');
    const distDir = path.join(rootDir, 'resources', 'python');

    // Clean up existing build and dist directories if they exist -- or name them, if they don't
    [buildDir, distDir].forEach(dir => {
        const dirPath = path.dirname(dir);
        if (fs.existsSync(dirPath)) {
            console.log(`🧹 Cleaning up ${dir}...`);
            try {
                fs.removeSync(dir);
                console.log(`✅ Successfully removed ${dir}`);
                // Create the directory again
                fs.mkdirSync(dirPath, { recursive: true });
            } catch (error) {
                console.error(`❌ Failed to remove ${dir}:`, error.message);
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
        // Add all hidden imports
        '--hidden-import=flask_cors',
        '--hidden-import=flask.app',
        '--hidden-import=python_dotenv',
        '--hidden-import=waitress',
        '--hidden-import=xlwings',
        '--hidden-import=anthropic',
        '--hidden-import=openpyxl',
        '--hidden-import=asgiref',
        '--hidden-import=uvicorn',
        '--hidden-import=fastapi',
        '--hidden-import=pydantic',
        // Add the python-server directory to the path
        '--paths', pythonDir,
        // Collect all Flask components
        '--collect-all', 'flask',
        '--collect-all', 'python_dotenv',
        '--collect-all', 'waitress',
        '--collect-data=xlwings',
        '--collect-data=anthropic',
        '--collect-all', 'fastapi',
        '--collect-all', 'uvicorn',
        '--collect-all', 'pydantic',
        '--collect-all', 'pydantic_core',
        '--collect-all', 'anyio',
        '--collect-all', 'starlette',
        '--collect-all', 'httpcore',
        '--collect-all', 'httpx',
        '--collect-all', 'openpyxl',
        '--collect-all', 'asgiref',
        '--name=python-server',        
        // Add all Python files in the python-server directory
        '--add-data', `${path.join(pythonDir, 'app.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, 'wsgi.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, 'asgi.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, '__init__.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, '*.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, 'excel')}${path.delimiter}excel`,
        // Entry point for prod server
        '--onefile',
        path.join(pythonDir, 'asgi.py')
    ];

    console.log('Running: pyinstaller', pyInstallerArgs.join(' '));
    
    // Execute build
    const result = spawn.sync('pyinstaller', pyInstallerArgs, {
        cwd: rootDir,
        stdio: 'inherit'
    });

    if (result.status !== 0) {
        console.error('❌ Python build failed');
        process.exit(1);
    }

    console.log('✅ Python build successful');
    
    // Ensure resources directory exists
    const resourcesDir = path.join(__dirname, '../../resources');
    if (!fs.existsSync(resourcesDir)) {
        fs.mkdirSync(resourcesDir, { recursive: true });
    }

    // Copy wsgi.py to resources
    const wsgiSource = path.join(__dirname, '../python-server/wsgi.py');
    const wsgiDest = path.join(__dirname, '../../resources/wsgi.py');
    fs.copyFileSync(wsgiSource, wsgiDest);
    console.log(`Copied wsgi.py to ${wsgiDest}`);

    // Copy asgi.py to resources
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
            console.log(`✅ Copied .env to ${envDest}`);
        } else {
            console.log('ℹ️  No .env file found to copy');
        }
    } catch (error) {
        console.warn('⚠️  Could not copy .env file:', error.message);
    }

    return true;
}

module.exports = { buildPython };

// Run if called directly
if (require.main === module) {
    buildPython();    
}
