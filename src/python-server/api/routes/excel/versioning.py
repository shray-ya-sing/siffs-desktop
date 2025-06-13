from fastapi import APIRouter, HTTPException, Response, Depends
from fastapi.responses import StreamingResponse
from pathlib import Path
import sys
# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from python-server
from excel.metadata.storage.excel_metadata_storage import ExcelMetadataStorage
import logging
# Get logger instance
logger = logging.getLogger(__name__)
import json
from typing import Generator


router = APIRouter(
    prefix="/api/excel/versioning",
    tags=["excel-versioning"],
)

# Dependency to get the storage instance
def get_storage() -> Generator[ExcelMetadataStorage, None, None]:
    try:
        storage = ExcelMetadataStorage()
        yield storage
    finally:
        # The singleton will handle its own cleanup via atexit
        pass

@app.get("/{file_path:path}/versions")
async def get_file_versions(
    file_path: str,
    storage: ExcelMetadataStorage = Depends(get_storage)
):
    blobs = storage.get_all_file_blobs(file_path)
    if not blobs:
        raise HTTPException(status_code=404, detail="No versions found")
    
    # Return metadata without the actual blob data
    return [{
        'version_id': b['version_id'],
        'version_number': b['version_number'],
        'created_at': b['created_at'],
        'change_description': b['change_description'],
        'file_hash': b['file_hash'],
        'download_url': f"/api/excel/{file_path}/versions/{b['version_id']}/download"
    } for b in blobs]

@app.get("/{file_path:path}/versions/{version_id}/download")
async def download_version(
    file_path: str,
    version_id: int,
    storage: ExcelMetadataStorage = Depends(get_storage)
):
    blob = storage.get_file_blob(file_path, version_id)
    if not blob:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return Response(
        content=blob,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=version_{version_id}.xlsx"
        }
    )