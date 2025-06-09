# excel/session_manager.py
from typing import Dict, Optional, Tuple
import xlwings as xw
from pathlib import Path
import threading
import os

class ExcelSessionManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super(ExcelSessionManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # Ensure __init__ is only called once
        if self._initialized:
            return
            
        self._sessions: Dict[str, Tuple[xw.App, xw.Book]] = {}
        self._default_app: Optional[xw.App] = None
        self._initialized = True
    
    def _get_or_create_app(self, visible: bool = False) -> xw.App:
        """Get the default app or create a new one if needed"""
        try:
            # Try to use existing default app if it's still valid
            if self._default_app:
                # Check if app is still alive by accessing a property
                _ = self._default_app.visible
                return self._default_app
        except:
            # App is no longer valid
            self._default_app = None
        
        # Create new default app
        self._default_app = xw.App(visible=visible, add_book=False)
        return self._default_app
    
    def get_session(self, file_path: str, visible: bool = False) -> Optional[xw.Book]:
        """Get or create a workbook session"""
        file_path = str(Path(file_path).resolve())
        
        # Check if we have an existing valid session
        if file_path in self._sessions:
            app, wb = self._sessions[file_path]
            try:
                # Verify the workbook is still valid
                _ = wb.name
                return wb
            except:
                # Workbook is no longer valid, remove from sessions
                del self._sessions[file_path]
        
        # Create new session
        try:
            app = self._get_or_create_app(visible)
            
            if Path(file_path).exists():
                # Check if workbook is already open in this app
                for book in app.books:
                    try:
                        if Path(book.fullname).resolve() == Path(file_path).resolve():
                            wb = book
                            break
                    except:
                        continue
                else:
                    wb = app.books.open(file_path)
            else:
                # Create directory if it doesn't exist
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                wb = app.books.add()
                wb.save(file_path)
            
            self._sessions[file_path] = (app, wb)
            return wb
            
        except Exception as e:
            print(f"Error creating Excel session: {e}")
            return None
    
    def close_session(self, file_path: str, save: bool = True) -> bool:
        """Close a workbook session"""
        file_path = str(Path(file_path).resolve())
        
        if file_path not in self._sessions:
            return False
            
        try:
            app, wb = self._sessions[file_path]
            
            # Save if requested
            if save:
                wb.save()
            
            # Close the workbook
            wb.close()
            
            # Remove from sessions
            del self._sessions[file_path]
            
            # Check if this app has any other open workbooks
            try:
                if len(app.books) == 0 and app != self._default_app:
                    # No more workbooks in this app, quit it
                    app.quit()
            except:
                pass  # App might already be closed
            
            return True
            
        except Exception as e:
            print(f"Error closing Excel session: {e}")
            # Try to remove from sessions anyway
            self._sessions.pop(file_path, None)
            return False
    
    def close_all_sessions(self, save: bool = True) -> None:
        """Close all workbook sessions and quit all apps"""
        # Close all workbooks
        for file_path in list(self._sessions.keys()):
            self.close_session(file_path, save=save)
        
        # Quit the default app if it exists
        if self._default_app:
            try:
                self._default_app.quit()
            except:
                pass
            self._default_app = None
        
        # Clear sessions
        self._sessions.clear()
    
    def save_session(self, file_path: str) -> bool:
        """Save a workbook without closing it"""
        file_path = str(Path(file_path).resolve())
        
        if file_path in self._sessions:
            try:
                _, wb = self._sessions[file_path]
                # Verify workbook is still valid
                _ = wb.name
                wb.save()
                return True
            except Exception as e:
                print(f"Error saving workbook: {e}")
                # Remove invalid session
                self._sessions.pop(file_path, None)
        
        return False
    
    def is_session_valid(self, file_path: str) -> bool:
        """Check if a session is still valid"""
        file_path = str(Path(file_path).resolve())
        
        if file_path not in self._sessions:
            return False
            
        try:
            _, wb = self._sessions[file_path]
            _ = wb.name  # This will raise if workbook is closed
            return True
        except:
            # Remove invalid session
            self._sessions.pop(file_path, None)
            return False
    
    def refresh_session(self, file_path: str) -> Optional[xw.Book]:
        """Refresh a session by closing and reopening"""
        file_path = str(Path(file_path).resolve())
        visible = False
        
        # Check if current session exists and get visibility
        if file_path in self._sessions:
            app, _ = self._sessions[file_path]
            try:
                visible = app.visible
            except:
                pass
            
            # Close existing session
            self.close_session(file_path, save=True)
        
        # Reopen
        return self.get_session(file_path, visible=visible)
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            self.close_all_sessions(save=True)
        except:
            pass

# Enhanced usage with context manager support
class ManagedExcelSession:
    """Context manager for Excel sessions"""
    
    def __init__(self, file_path: str, visible: bool = False, save_on_exit: bool = True):
        self.file_path = file_path
        self.visible = visible
        self.save_on_exit = save_on_exit
        self.manager = ExcelSessionManager()
        self.workbook = None
    
    def __enter__(self) -> xw.Book:
        self.workbook = self.manager.get_session(self.file_path, self.visible)
        if not self.workbook:
            raise RuntimeError(f"Failed to open workbook: {self.file_path}")
        return self.workbook
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.workbook:
            self.manager.close_session(self.file_path, save=self.save_on_exit)
