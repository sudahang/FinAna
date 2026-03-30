"""SeaweedFS client for storing full reports."""

import io
import requests
from typing import Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SeaweedClient:
    """
    SeaweedFS client for storing full reports.

    Features:
    - Upload files to SeaweedFS Filer
    - Download files by fid
    - Delete files
    - Organize files by directory structure
    """

    def __init__(
        self,
        filer_url: str = "http://localhost:8888",
        master_url: str = "http://localhost:9333",
        timeout: int = 30,
    ):
        """
        Initialize SeaweedFS client.

        Args:
            filer_url: SeaweedFS Filer URL
            master_url: SeaweedFS Master URL
            timeout: Request timeout in seconds
        """
        self.filer_url = filer_url.rstrip("/")
        self.master_url = master_url.rstrip("/")
        self.timeout = timeout

        # Session for connection pooling
        self.session = requests.Session()

    def test_connection(self) -> bool:
        """Test SeaweedFS connection."""
        try:
            response = self.session.get(
                f"{self.filer_url}/",
                timeout=self.timeout
            )
            return response.status_code < 400
        except requests.RequestException as e:
            logger.error(f"SeaweedFS connection failed: {e}")
            return False

    def upload_report(
        self,
        report_content: str,
        report_id: str,
        metadata: dict = None,
        directory: str = "/reports"
    ) -> Optional[str]:
        """
        Upload a report to SeaweedFS.

        Args:
            report_content: Report content (markdown text)
            report_id: Unique report identifier
            metadata: Report metadata
            directory: Directory path in Filer

        Returns:
            File ID (fid) if successful, None otherwise
        """
        try:
            # Create directory if not exists
            self._ensure_directory(directory)

            # Prepare file path
            file_path = f"{directory}/{report_id}.md"

            # Prepare metadata JSON
            import json
            if metadata is None:
                metadata = {}

            metadata["uploaded_at"] = datetime.now().isoformat()
            metadata["content_type"] = "text/markdown"
            metadata["report_id"] = report_id

            # Upload via Filer API
            upload_url = f"{self.filer_url}{file_path}"

            headers = {
                "Content-Type": "text/markdown; charset=utf-8",
            }

            # Add metadata as custom headers
            for key, value in metadata.items():
                headers[f"X-Seaweedfs-Meta-{key}"] = str(value)

            response = self.session.put(
                upload_url,
                data=report_content.encode("utf-8"),
                headers=headers,
                timeout=self.timeout
            )

            if response.status_code in (200, 201):
                logger.info(f"Report uploaded: {file_path}")
                return report_id
            else:
                logger.error(f"Upload failed: {response.status_code} - {response.text}")
                return None

        except requests.RequestException as e:
            logger.error(f"Failed to upload report: {e}")
            return None

    def upload_file(
        self,
        content: Union[str, bytes, io.BytesIO],
        file_path: str,
        content_type: str = "application/octet-stream"
    ) -> Optional[str]:
        """
        Upload any file to SeaweedFS.

        Args:
            content: File content (string, bytes, or file-like object)
            file_path: Full path in Filer (e.g., /reports/2024/01/report.md)
            content_type: MIME type of the file

        Returns:
            File path if successful, None otherwise
        """
        try:
            # Create parent directory
            directory = "/".join(file_path.split("/")[:-1])
            self._ensure_directory(directory)

            # Handle different content types
            if isinstance(content, str):
                data = content.encode("utf-8")
            elif isinstance(content, io.BytesIO):
                data = content.getvalue()
            else:
                data = content

            upload_url = f"{self.filer_url}{file_path}"

            response = self.session.put(
                upload_url,
                data=data,
                headers={"Content-Type": content_type},
                timeout=self.timeout
            )

            if response.status_code in (200, 201):
                logger.info(f"File uploaded: {file_path}")
                return file_path
            else:
                logger.error(f"Upload failed: {response.status_code} - {response.text}")
                return None

        except requests.RequestException as e:
            logger.error(f"Failed to upload file: {e}")
            return None

    def download_report(self, report_id: str, directory: str = "/reports") -> Optional[str]:
        """
        Download a report from SeaweedFS.

        Args:
            report_id: Report identifier
            directory: Directory path

        Returns:
            Report content if successful, None otherwise
        """
        try:
            file_path = f"{directory}/{report_id}.md"
            download_url = f"{self.filer_url}{file_path}"

            response = self.session.get(
                download_url,
                timeout=self.timeout
            )

            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                logger.warning(f"Report not found: {file_path}")
                return None
            else:
                logger.error(f"Download failed: {response.status_code}")
                return None

        except requests.RequestException as e:
            logger.error(f"Failed to download report: {e}")
            return None

    def download_file(self, file_path: str) -> Optional[bytes]:
        """
        Download any file from SeaweedFS.

        Args:
            file_path: Full path in Filer

        Returns:
            File content if successful, None otherwise
        """
        try:
            download_url = f"{self.filer_url}{file_path}"

            response = self.session.get(
                download_url,
                timeout=self.timeout
            )

            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Download failed: {response.status_code}")
                return None

        except requests.RequestException as e:
            logger.error(f"Failed to download file: {e}")
            return None

    def delete_report(self, report_id: str, directory: str = "/reports") -> bool:
        """
        Delete a report from SeaweedFS.

        Args:
            report_id: Report identifier
            directory: Directory path

        Returns:
            True if successful, False otherwise
        """
        file_path = f"{directory}/{report_id}.md"
        return self.delete_file(file_path)

    def delete_file(self, file_path: str) -> bool:
        """
        Delete any file from SeaweedFS.

        Args:
            file_path: Full path in Filer

        Returns:
            True if successful, False otherwise
        """
        try:
            delete_url = f"{self.filer_url}{file_path}"

            response = self.session.delete(
                delete_url,
                timeout=self.timeout
            )

            if response.status_code in (200, 204):
                logger.info(f"File deleted: {file_path}")
                return True
            else:
                logger.error(f"Delete failed: {response.status_code}")
                return False

        except requests.RequestException as e:
            logger.error(f"Failed to delete file: {e}")
            return False

    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in SeaweedFS.

        Args:
            file_path: Full path in Filer

        Returns:
            True if file exists, False otherwise
        """
        try:
            check_url = f"{self.filer_url}{file_path}"

            response = self.session.head(
                check_url,
                timeout=self.timeout
            )

            return response.status_code == 200

        except requests.RequestException:
            return False

    def report_exists(self, report_id: str, directory: str = "/reports") -> bool:
        """
        Check if a report exists in SeaweedFS.

        Args:
            report_id: Report identifier
            directory: Directory path

        Returns:
            True if report exists, False otherwise
        """
        file_path = f"{directory}/{report_id}.md"
        return self.file_exists(file_path)

    def list_reports(
        self,
        directory: str = "/reports",
        limit: int = 100
    ) -> list[dict]:
        """
        List reports in a directory.

        Args:
            directory: Directory path
            limit: Maximum number of results

        Returns:
            List of report metadata
        """
        try:
            list_url = f"{self.filer_url}/dir{directory}"

            response = self.session.get(
                list_url,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                entries = data.get("Entries", [])

                reports = []
                for entry in entries:
                    if entry.get("Name", "").endswith(".md"):
                        reports.append({
                            "name": entry["Name"],
                            "size": entry.get("Size", 0),
                            "mtime": entry.get("Attributes", {}).get("mtime", ""),
                        })

                return reports[:limit]
            else:
                return []

        except requests.RequestException as e:
            logger.error(f"Failed to list reports: {e}")
            return []

    def _ensure_directory(self, directory: str) -> bool:
        """
        Ensure a directory exists in Filer.

        Args:
            directory: Directory path to create

        Returns:
            True if successful or already exists
        """
        if not directory:
            return True

        try:
            mkdir_url = f"{self.filer_url}/dir{directory}?overwrite=false"

            response = self.session.post(
                mkdir_url,
                timeout=self.timeout
            )

            # 200 or 201 means created, 409 means already exists
            return response.status_code in (200, 201, 409)

        except requests.RequestException:
            return False

    def get_stats(self) -> dict:
        """Get SeaweedFS cluster statistics."""
        try:
            response = self.session.get(
                f"{self.master_url}/cluster/status",
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "volumes": data.get("Volumes", 0),
                    "max_volume_id": data.get("MaxVolumeId", 0),
                    "connected": True,
                }
            else:
                return {"connected": False}

        except requests.RequestException as e:
            logger.error(f"Failed to get stats: {e}")
            return {"connected": False, "error": str(e)}

    def close(self):
        """Close the session."""
        self.session.close()


_seaweed_client: Optional[SeaweedClient] = None


def get_seaweed_client(
    filer_url: str = None,
    master_url: str = None
) -> SeaweedClient:
    """
    Get or create SeaweedFS client singleton.

    Args:
        filer_url: Override SeaweedFS Filer URL
        master_url: Override SeaweedFS Master URL

    Returns:
        SeaweedClient instance
    """
    global _seaweed_client

    if _seaweed_client is None:
        import os

        filer_url = filer_url or os.getenv("SEAWEED_FILER_URL", "http://localhost:8888")
        master_url = master_url or os.getenv("SEAWEED_MASTER_URL", "http://localhost:9333")

        _seaweed_client = SeaweedClient(
            filer_url=filer_url,
            master_url=master_url,
        )

    return _seaweed_client
