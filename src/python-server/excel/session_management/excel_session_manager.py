# excel/session_manager.py
from typing import Dict, Optional, Tuple
import xlwings as xw
from pathlib import Path
import threading
import os
import logging
logger = logging.getLogger(__name__)

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
            # First try to get an existing app instance
            existing_app = self.get_existing_excel_app()
            if existing_app:
                self._app = existing_app
                logger.info("Using existing Excel app instance running on user machine")
                return self._app
            
            # If we got here, there is no existing app instance running on user machine, so create a new one
            logger.info("Creating new Excel app instance")
            self._app = xw.App(visible=visible, add_book=False)
            return self._app
        else:
            logger.info("Using existing Excel app instance")
            # This means the app instance is set on the session manager.
            # But we need to check if its still alive or it was terminated before trying to use it
            try:
                # Active app object will return an array of 0 or more books
                books = self._app.books
                if not books:
                    # If no books, the app is terminated. Create a new one.
                    logger.info("Existing app is terminated. Creating new Excel app instance")
                    self._app = xw.App(visible=visible, add_book=False)
            except:
                # Error means the app is terminated. Create a new one.
                logger.info("Error getting books from app. Implies app is terminated. Creating new Excel app instance")
                self._app = xw.App(visible=visible, add_book=False)
            
            return self._app

    def get_existing_excel_app(self) -> Optional[xw.App]:
        """Get an existing Excel application instance or None if none is running."""
        try:
            # Get all running Excel instances
            apps = xw.apps
            
            if len(apps) > 0:
                # Return the first running instance
                return apps[0]
            return None
            
        except Exception as e:
            print(f"Error getting Excel instance: {e}")
            return None
    
    def get_session(self, file_path: str, visible: bool = _visible) -> Optional[xw.Book]:
        """Get or create a workbook session"""
        file_path = str(Path(file_path).resolve())
        
        # Check if the filepath is in the sessions dictionary. 
        # If yes, then we need to check if the old app and wb instances are still valid and should be reused
        # If invalid, we need to reinitialize them for that entry
        if file_path in self._sessions:
            print(f"Session found for {file_path}")
            app, wb = self._sessions[file_path]
            try:
                # Check if the app is still valid
                _ = app.books
            except:
                print(f"App is terminated for {file_path}")
                # If the app is terminated, we need to reinitialize it and the workbook
                # Remove the invalid session
                self._sessions.pop(file_path, None)
                # Reinitialize the app and workbook
                app = self._ensure_app(visible)
                wb = app.books.open(file_path)
                self._sessions[file_path] = (app, wb)
                print(f"Reinitialized app and workbook for {file_path}")
                return wb
            # If app is valid, check if the workbook is still valid
            try:
                _ = wb.name  # Check if workbook is still valid
                print(f"Workbook is valid for {file_path}")
                return wb
            except:
                # App is valid but workbook is invalid or terminated. Let's open the workbook again
                # Remove the invalid session
                print(f"Workbook is terminated for {file_path}")
                self._sessions.pop(file_path, None)
                # Reinitialize the workbook
                app = self._ensure_app(visible)
                wb = app.books.open(file_path)
                self._sessions[file_path] = (app, wb)
                print(f"Reinitialized workbook for {file_path}")
                return wb
        
        # Filepath was never added to sessions. Create new entry for it in sessions
        try:
            print(f"Creating new session for {file_path}")
            app = self._ensure_app(visible)
            print(f"App is valid for {file_path}")
            # If the file exists, check if it's open in our app
            if Path(file_path).exists():
                # Check if already open in our app
                for book in app.books:
                    try:
                        if Path(book.fullname).resolve() == Path(file_path).resolve():
                            print(f"Workbook is already open for {file_path}, returning existing book")
                            # If open, just return that workbook
                            wb = book
                            return wb
                    except:
                        continue
                print(f"Workbook is not open for {file_path}, opening it")
                # If we don't have the workbook open, open it
                wb = app.books.open(file_path)
            # If it doesn't exist, create it
            else:
                print(f"Workbook does not exist for {file_path}, creating it")
                # Create new workbook
                os.makedirs(Path(file_path).parent, exist_ok=True)
                wb = app.books.add()
                wb.save(file_path)
            
            self._sessions[file_path] = (app, wb)
            print(f"New session created for {file_path}")
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
            # Verify workbook is still valid
            try:
                _ = wb.name
                print(f"Workbook is valid for {file_path}, saving and closing")
                if save:
                    wb.save()
                wb.close()
                # Check if the app needs to be closed
                if app and not any(wb for _, wb in self._sessions.values()):
                    print(f"No more workbooks for {file_path}, closing app")
                    # This means the app is still set on the session 
                    try:
                        # if the app instance still valid it will quit
                        app.quit()
                        self._app = None
                        print(f"App closed for {file_path}")
                    except:
                        print(f"App is terminated for {file_path}")
                        self._app = None # Set the app to None to prevent it from being used
                        pass

                self._sessions.pop(file_path, None) 
                print(f" Session cleared and Workbook closed for {file_path}")
                
            except:
                # Workbook or App is invalid or terminated and can no longer be accessed. Remove the session
                self._sessions.pop(file_path, None)
                if self._app:
                    self._app = None # Clear app instance on class
                wb = None # Clear workbook instance on class
                print(f"Workbook or App is invalid or terminated for {file_path}, cleared session and instances")
                return True

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
            app, wb = self._sessions[file_path]
            if app is None or wb is None:
                return False
            # Check if app is valid
            try: 
                books = app.books
                _ = wb.name
                return True
            except:
                # app is invalid
                return False
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
