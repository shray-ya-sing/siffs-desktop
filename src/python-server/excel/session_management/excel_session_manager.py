# excel/session_manager.py
from typing import Dict, Optional, Tuple
import xlwings as xw
from pathlib import Path
import threading
import os

class ExcelSessionManager:
    _instance = None
    _lock = threading.Lock()
    _visible = True
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ExcelSessionManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._sessions = {}  # file_path -> (app, wb)
        self._app = None  # Lazy initialization
        self._initialized = True
    
    def _ensure_app(self, visible: bool = _visible) -> xw.App:
        """Ensure we have an Excel app instance, creating if needed"""
        if self._app is None:
            self._app = xw.App(visible=visible, add_book=False)
        return self._app
    
    def get_session(self, file_path: str, visible: bool = _visible) -> Optional[xw.Book]:
        """Get or create a workbook session"""
        file_path = str(Path(file_path).resolve())
        
        # Return existing session if valid
        if file_path in self._sessions:
            app, wb = self._sessions[file_path]
            try:
                _ = wb.name  # Check if workbook is still valid
                return wb
            except:
                # Clean up invalid session
                self._sessions.pop(file_path, None)
                if app and not any(wb for _, wb in self._sessions.values()):
                    try:
                        app.quit()
                    except:
                        pass
                    self._app = None
        
        # Create new session
        try:
            app = self._ensure_app(visible)
            
            if Path(file_path).exists():
                # Check if already open in our app
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
                # Create new workbook
                os.makedirs(Path(file_path).parent, exist_ok=True)
                wb = app.books.add()
                wb.save(file_path)
            
            self._sessions[file_path] = (app, wb)
            return wb
            
        except Exception as e:
            print(f"Error creating Excel session: {e}")
            # Clean up app if no workbooks
            if self._app and not self._app.books:
                try:
                    self._app.quit()
                except:
                    pass
                self._app = None
            return None
    
    def close_session(self, file_path: str, save: bool = True) -> bool:
        """Close a workbook session"""
        file_path = str(Path(file_path).resolve())
        
        if file_path not in self._sessions:
            return False
            
        try:
            app, wb = self._sessions[file_path]
            
            if save:
                wb.save()
            
            wb.close()
            self._sessions.pop(file_path, None)
            
            # Clean up app if no more workbooks
            if app and not any(wb for _, wb in self._sessions.values()):
                try:
                    app.quit()
                except:
                    pass
                self._app = None
                
            return True
            
        except Exception as e:
            print(f"Error closing Excel session: {e}")
            self._sessions.pop(file_path, None)
            return False
    
    def close_all_sessions(self, save: bool = True) -> None:
        """Close all workbook sessions and cleanup"""
        for file_path in list(self._sessions.keys()):
            self.close_session(file_path, save=save)
        
        # Should be cleaned up by close_session, but just in case
        if hasattr(self, '_app') and self._app is not None:
            try:
                self._app.quit()
            except:
                pass
            self._app = None
        
        self._sessions.clear()
    
    def save_session(self, file_path: str) -> bool:
        """Save a workbook without closing it"""
        file_path = str(Path(file_path).resolve())
        
        if file_path in self._sessions:
            try:
                _, wb = self._sessions[file_path]
                _ = wb.name  # Verify workbook is still valid
                wb.save()
                return True
            except Exception as e:
                print(f"Error saving workbook: {e}")
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
        visible = _visible
        
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
    
    def __init__(self, file_path: str, visible: bool = True, save_on_exit: bool = True):
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
