"""Cloud storage integration for content ingestion"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import io
import os
from pathlib import Path

from .content_ingestor import ContentSource, ContentItem, ContentProcessor

logger = logging.getLogger(__name__)


class CloudStorageBase(ContentSource):
    """Base class for cloud storage sources"""
    
    def __init__(self, config: Dict[str, Any]):
        self.folder_id = config.get('folder_id', '')
        self.recursive = config.get('recursive', True)
        self.max_depth = config.get('max_depth', 5)
        self.processor = ContentProcessor()
        self.supported_extensions = {'.txt', '.md', '.html', '.json', '.csv', '.docx', '.pdf'}
    
    def _should_process_file(self, filename: str) -> bool:
        """Check if file should be processed based on extension"""
        return any(filename.lower().endswith(ext) for ext in self.supported_extensions)


class GoogleDriveSource(CloudStorageBase):
    """Google Drive content source"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service = None
        self._init_service()
    
    def _init_service(self):
        """Initialize Google Drive service"""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            # Check for credentials
            creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not creds_path:
                logger.warning("GOOGLE_APPLICATION_CREDENTIALS not set")
                return
            
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            
            self.service = build('drive', 'v3', credentials=credentials)
            logger.info("Google Drive service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive: {e}")
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """Validate Google Drive configuration"""
        errors = []
        
        if not self.folder_id:
            errors.append("Google Drive folder_id not specified")
        
        if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            errors.append("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
        
        if not self.service:
            errors.append("Failed to initialize Google Drive service")
        
        return len(errors) == 0, errors
    
    def ingest(self) -> List[ContentItem]:
        """Ingest content from Google Drive"""
        if not self.service:
            logger.error("Google Drive service not initialized")
            return []
        
        items = []
        logger.info(f"Ingesting from Google Drive folder: {self.folder_id}")
        
        try:
            # Get files from folder
            files = self._list_files_recursive(self.folder_id, 0)
            
            for file_info in files:
                content_item = self._process_file(file_info)
                if content_item:
                    items.append(content_item)
            
            logger.info(f"Processed {len(files)} files from Google Drive")
            
        except Exception as e:
            logger.error(f"Error during Google Drive ingestion: {e}")
        
        return items
    
    def _list_files_recursive(self, folder_id: str, depth: int) -> List[Dict]:
        """List files recursively from Google Drive folder"""
        if depth > self.max_depth:
            return []
        
        files = []
        
        try:
            # List files in current folder
            query = f"'{folder_id}' in parents and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, size, modifiedTime)"
            ).execute()
            
            for item in results.get('files', []):
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    # Recursively process subfolder
                    if self.recursive:
                        files.extend(self._list_files_recursive(item['id'], depth + 1))
                else:
                    # Add file if supported
                    if self._should_process_file(item['name']):
                        files.append(item)
            
        except Exception as e:
            logger.error(f"Error listing files in folder {folder_id}: {e}")
        
        return files
    
    def _process_file(self, file_info: Dict) -> Optional[ContentItem]:
        """Process a single file from Google Drive"""
        try:
            file_id = file_info['id']
            filename = file_info['name']
            
            logger.debug(f"Processing Google Drive file: {filename}")
            
            # Download file content
            if file_info['mimeType'].startswith('application/vnd.google-apps'):
                # Google Docs/Sheets need export
                content = self._export_google_doc(file_id, file_info['mimeType'])
            else:
                # Regular files
                content = self._download_file(file_id)
            
            if not content:
                return None
            
            # Process content based on type
            file_ext = Path(filename).suffix.lower()
            if file_ext == '.md':
                processed_content = self.processor.process_markdown(content)
            elif file_ext in ['.html', '.htm']:
                processed_content = self.processor.process_html(content)
            elif file_ext == '.json':
                processed_content = self.processor.process_json(content)
            elif file_ext == '.csv':
                processed_content = self.processor.process_csv(content)
            else:
                processed_content = self.processor.process_text(content, file_ext)
            
            # Create metadata
            metadata = {
                'source': 'google_drive',
                'file_id': file_id,
                'filename': filename,
                'mime_type': file_info['mimeType'],
                'size': file_info.get('size', 0),
                'modified': file_info.get('modifiedTime', ''),
                'ingested_at': datetime.now().isoformat()
            }
            
            return ContentItem(processed_content, metadata)
            
        except Exception as e:
            logger.error(f"Error processing file {file_info.get('name', 'unknown')}: {e}")
            return None
    
    def _download_file(self, file_id: str) -> Optional[str]:
        """Download file content from Google Drive"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            content = request.execute()
            
            # Decode if text
            if isinstance(content, bytes):
                try:
                    return content.decode('utf-8')
                except:
                    logger.warning(f"Could not decode file {file_id} as text")
                    return None
            
            return content
            
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            return None
    
    def _export_google_doc(self, file_id: str, mime_type: str) -> Optional[str]:
        """Export Google Docs/Sheets to text format"""
        try:
            # Determine export format
            if 'document' in mime_type:
                export_mime = 'text/plain'
            elif 'spreadsheet' in mime_type:
                export_mime = 'text/csv'
            elif 'presentation' in mime_type:
                export_mime = 'text/plain'
            else:
                logger.warning(f"Unknown Google Apps type: {mime_type}")
                return None
            
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType=export_mime
            )
            content = request.execute()
            
            if isinstance(content, bytes):
                return content.decode('utf-8')
            
            return content
            
        except Exception as e:
            logger.error(f"Error exporting Google Doc {file_id}: {e}")
            return None


class OneDriveSource(CloudStorageBase):
    """OneDrive content source"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize OneDrive client"""
        try:
            from msal import ConfidentialClientApplication
            import requests
            
            # Check for credentials
            client_id = os.getenv('ONEDRIVE_CLIENT_ID')
            client_secret = os.getenv('ONEDRIVE_CLIENT_SECRET')
            tenant_id = os.getenv('ONEDRIVE_TENANT_ID')
            
            if not all([client_id, client_secret, tenant_id]):
                logger.warning("OneDrive credentials not fully configured")
                return
            
            # Initialize MSAL app
            app = ConfidentialClientApplication(
                client_id,
                authority=f"https://login.microsoftonline.com/{tenant_id}",
                client_credential=client_secret
            )
            
            # Get token
            result = app.acquire_token_silent(
                ["https://graph.microsoft.com/.default"],
                account=None
            )
            
            if not result:
                result = app.acquire_token_for_client(
                    scopes=["https://graph.microsoft.com/.default"]
                )
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                self.headers = {'Authorization': f'Bearer {self.access_token}'}
                logger.info("OneDrive client initialized")
            else:
                logger.error(f"Failed to get OneDrive token: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Failed to initialize OneDrive: {e}")
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """Validate OneDrive configuration"""
        errors = []
        
        if not self.folder_id:
            errors.append("OneDrive folder_id not specified")
        
        required_env = ['ONEDRIVE_CLIENT_ID', 'ONEDRIVE_CLIENT_SECRET', 'ONEDRIVE_TENANT_ID']
        for env_var in required_env:
            if not os.getenv(env_var):
                errors.append(f"{env_var} environment variable not set")
        
        if not hasattr(self, 'access_token'):
            errors.append("Failed to initialize OneDrive client")
        
        return len(errors) == 0, errors
    
    def ingest(self) -> List[ContentItem]:
        """Ingest content from OneDrive"""
        # Simplified implementation - would need full Graph API integration
        logger.warning("OneDrive ingestion not fully implemented")
        return []


class DropboxSource(CloudStorageBase):
    """Dropbox content source"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.dbx = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Dropbox client"""
        try:
            import dropbox
            
            access_token = os.getenv('DROPBOX_ACCESS_TOKEN')
            if not access_token:
                logger.warning("DROPBOX_ACCESS_TOKEN not set")
                return
            
            self.dbx = dropbox.Dropbox(access_token)
            
            # Test connection
            try:
                self.dbx.users_get_current_account()
                logger.info("Dropbox client initialized")
            except:
                logger.error("Invalid Dropbox access token")
                self.dbx = None
                
        except ImportError:
            logger.error("Dropbox SDK not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Dropbox: {e}")
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """Validate Dropbox configuration"""
        errors = []
        
        if not self.folder_id:
            errors.append("Dropbox folder path not specified")
        
        if not os.getenv('DROPBOX_ACCESS_TOKEN'):
            errors.append("DROPBOX_ACCESS_TOKEN environment variable not set")
        
        if not self.dbx:
            errors.append("Failed to initialize Dropbox client")
        
        return len(errors) == 0, errors
    
    def ingest(self) -> List[ContentItem]:
        """Ingest content from Dropbox"""
        if not self.dbx:
            logger.error("Dropbox client not initialized")
            return []
        
        items = []
        logger.info(f"Ingesting from Dropbox folder: {self.folder_id}")
        
        try:
            # List files in folder
            files = self._list_files_recursive(self.folder_id, 0)
            
            for file_metadata in files:
                content_item = self._process_file(file_metadata)
                if content_item:
                    items.append(content_item)
            
            logger.info(f"Processed {len(files)} files from Dropbox")
            
        except Exception as e:
            logger.error(f"Error during Dropbox ingestion: {e}")
        
        return items
    
    def _list_files_recursive(self, folder_path: str, depth: int) -> List[Any]:
        """List files recursively from Dropbox folder"""
        if depth > self.max_depth:
            return []
        
        files = []
        
        try:
            result = self.dbx.files_list_folder(folder_path)
            
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    if self._should_process_file(entry.name):
                        files.append(entry)
                elif isinstance(entry, dropbox.files.FolderMetadata) and self.recursive:
                    files.extend(self._list_files_recursive(entry.path_display, depth + 1))
            
        except Exception as e:
            logger.error(f"Error listing Dropbox folder {folder_path}: {e}")
        
        return files
    
    def _process_file(self, file_metadata) -> Optional[ContentItem]:
        """Process a single file from Dropbox"""
        try:
            logger.debug(f"Processing Dropbox file: {file_metadata.name}")
            
            # Download file
            _, response = self.dbx.files_download(file_metadata.path_display)
            content = response.content.decode('utf-8')
            
            # Process content
            file_ext = Path(file_metadata.name).suffix.lower()
            if file_ext == '.md':
                processed_content = self.processor.process_markdown(content)
            elif file_ext in ['.html', '.htm']:
                processed_content = self.processor.process_html(content)
            elif file_ext == '.json':
                processed_content = self.processor.process_json(content)
            elif file_ext == '.csv':
                processed_content = self.processor.process_csv(content)
            else:
                processed_content = self.processor.process_text(content, file_ext)
            
            # Create metadata
            metadata = {
                'source': 'dropbox',
                'path': file_metadata.path_display,
                'filename': file_metadata.name,
                'size': file_metadata.size,
                'modified': file_metadata.server_modified.isoformat(),
                'ingested_at': datetime.now().isoformat()
            }
            
            return ContentItem(processed_content, metadata)
            
        except Exception as e:
            logger.error(f"Error processing Dropbox file {file_metadata.name}: {e}")
            return None