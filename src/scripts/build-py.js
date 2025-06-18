// Build script to create a single-file Python executable for the server
//
// Usage: node build-py.js
// IMPORTANT NOTE: always run this script from the ROOT directory of the project, otherwise path resolution will fail and the script will not run successfully
// 
// This script will build a single-file Python executable for the server
// and place it in the resources directory.
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
        '--hidden-import=numpy',
        '--hidden-import=tqdm',
        '--hidden-import=requests',
        '--hidden-import=packaging',
        '--hidden-import=filelock',
        '--hidden-import=huggingface_hub',
        '--hidden-import=pandas',
        '--hidden-import=sqlalchemy',
        '--hidden-import=faiss_cpu',
        '--hidden-import=sentence_transformers',
        '--hidden-import=httpcore',
        '--hidden-import=httpx',
        '--hidden-import=sklearn',
        '--hidden-import=transformers',
        '--hidden-import=tokenizers',
        '--hidden-import=torch',
        '--hidden-import=regex._regex',     
        '--hidden-import=langgraph',
        '--hidden-import=langchain',
        '--hidden-import=langchain-anthropic',
        '--hidden-import=langchain-openai',   
        '--hidden-import=voyageai',
        // copy metadata needed by transformers lib
        '--copy-metadata', 'regex',
        '--copy-metadata', 'requests',
        '--copy-metadata', 'packaging',
        '--copy-metadata', 'filelock',
        '--copy-metadata', 'numpy',
        '--copy-metadata', 'tokenizers',
        '--copy-metadata', 'tqdm',
        '--copy-metadata', 'huggingface_hub',
        '--copy-metadata', 'safetensors',
        '--copy-metadata', 'pyyaml',
        '--copy-metadata', 'transformers',
        '--copy-metadata', 'sentence_transformers',
        '--copy-metadata', 'torch',
        '--copy-metadata', 'scikit-learn',
        '--copy-metadata', 'scipy',
        '--copy-metadata', 'joblib',
        '--copy-metadata', 'threadpoolctl',
        '--copy-metadata', 'certifi',
        '--copy-metadata', 'charset_normalizer',
        '--copy-metadata', 'idna',
        '--copy-metadata', 'urllib3',    
        '--copy-metadata', 'langgraph',
        '--copy-metadata', 'langchain',
        '--copy-metadata', 'langchain-anthropic',
        '--copy-metadata', 'langchain-openai',
        '--copy-metadata', 'voyageai',
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
        '--collect-all', 'numpy',
        '--collect-all', 'pandas',
        '--collect-all', 'sqlalchemy',
        '--collect-all', 'faiss_cpu',
        '--collect-all', 'sentence_transformers',
        '--collect-all', 'sklearn',
        '--collect-all', 'transformers',
        '--collect-all', 'tokenizers',
        '--collect-all', 'torch',
        '--collect-all', 'tqdm',
        '--collect-all', 'requests',
        '--collect-all', 'packaging',
        '--collect-all', 'filelock',
        '--collect-all', 'huggingface_hub',
        '--collect-all', 'langgraph',
        '--collect-all', 'langchain',
        '--collect-all', 'langchain-anthropic',
        '--collect-all', 'langchain-openai',
        '--collect-all', 'voyageai',
        // Name of the main python server dir
        '--name=python-server',        
        // Add all Python files in the python-server directory
        '--add-data', `${path.join(pythonDir, 'app.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, 'wsgi.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, 'asgi.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, '__init__.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, 'logging_config.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, '*.py')}${path.delimiter}.`,
        '--add-data', `${path.join(pythonDir, 'excel')}${path.delimiter}excel`,
        '--add-data', `${path.join(pythonDir, 'ai_services')}${path.delimiter}ai_services`,
        '--add-data', `${path.join(pythonDir, 'api')}${path.delimiter}api`,
        '--add-data', `${path.join(pythonDir, 'core')}${path.delimiter}core`,
        '--add-data', `${path.join(pythonDir, 'vectors')}${path.delimiter}vectors`,
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
