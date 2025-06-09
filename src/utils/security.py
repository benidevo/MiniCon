"""Security utilities for safe system operations."""

import logging
import os
import subprocess
from pathlib import Path
from typing import List

from src.constants import (
    ALLOWED_CONTAINER_NAME_CHARS,
    ALLOWED_HOSTNAME_CHARS,
    DANGEROUS_COMMANDS,
    DEFAULT_SAFE_PATH_BASE,
    MAX_CONTAINER_NAME_LENGTH,
    MAX_HOSTNAME_LENGTH,
)

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when a security violation is detected."""


def is_safe_path(path: str, allowed_base: str = DEFAULT_SAFE_PATH_BASE) -> bool:
    """Check if a path is safe (no directory traversal).

    Args:
        path: The path to validate
        allowed_base: The base directory that paths must be within

    Returns:
        True if the path is safe, False otherwise
    """
    try:
        resolved_path = Path(path).resolve()
        allowed_path = Path(allowed_base).resolve()

        # Check if the path is within the allowed base directory
        return str(resolved_path).startswith(str(allowed_path))
    except (OSError, ValueError):
        return False


def validate_container_name(name: str) -> bool:
    """Validate container name for security.

    Args:
        name: Container name to validate

    Returns:
        True if name is valid, False otherwise
    """
    if not name or len(name) > MAX_CONTAINER_NAME_LENGTH:
        return False

    # Allow alphanumeric, hyphens, and underscores only
    return all(c in ALLOWED_CONTAINER_NAME_CHARS for c in name)


def validate_command(command: List[str]) -> bool:
    """Validate command arguments.

    Args:
        command: List of command arguments

    Returns:
        True if command is valid, False otherwise
    """
    if not command or len(command) == 0:
        return False

    # Check for potentially dangerous commands
    executable = os.path.basename(command[0])
    if executable in DANGEROUS_COMMANDS:
        logger.warning(f"Potentially dangerous command blocked: {executable}")
        return False

    return True


def safe_copy_directory(source: str, destination: str) -> None:
    """Safely copy directory contents without shell injection.

    Args:
        source: Source directory path
        destination: Destination directory path

    Raises:
        SecurityError: If paths are invalid or unsafe
        subprocess.CalledProcessError: If copy operation fails
    """
    if not os.path.exists(source) or not os.path.isdir(source):
        raise SecurityError(f"Invalid source directory: {source}")

    if not is_safe_path(destination):
        raise SecurityError(f"Unsafe destination path: {destination}")

    if not is_safe_path(source):
        raise SecurityError(f"Unsafe source path: {source}")

    try:
        # Use cp -a to preserve attributes and copy recursively
        subprocess.run(
            ["cp", "-a", f"{source}/.", destination],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(f"Successfully copied {source} to {destination}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to copy directory: {e.stderr}")
        raise


def safe_extract_tar(tar_path: str, destination: str) -> None:
    """Safely extract tar file without shell injection.

    Args:
        tar_path: Path to tar file
        destination: Destination directory

    Raises:
        SecurityError: If paths are invalid or unsafe
        subprocess.CalledProcessError: If extraction fails
    """
    if not os.path.exists(tar_path) or not tar_path.endswith(".tar"):
        raise SecurityError(f"Invalid tar file: {tar_path}")

    if not is_safe_path(destination):
        raise SecurityError(f"Unsafe destination path: {destination}")

    if not is_safe_path(tar_path):
        raise SecurityError(f"Unsafe tar file path: {tar_path}")

    try:
        subprocess.run(
            ["tar", "-xf", tar_path, "-C", destination],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(f"Successfully extracted {tar_path} to {destination}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to extract tar file: {e.stderr}")
        raise


def safe_mount_proc(proc_path: str) -> None:
    """Safely mount proc filesystem.

    Args:
        proc_path: Path where to mount proc

    Raises:
        SecurityError: If path is unsafe
        subprocess.CalledProcessError: If mount fails
    """
    if not is_safe_path(proc_path):
        raise SecurityError(f"Unsafe proc path: {proc_path}")

    try:
        subprocess.run(
            ["mount", "-t", "proc", "proc", proc_path],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(f"Successfully mounted proc at {proc_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to mount proc: {e.stderr}")
        raise


def safe_set_hostname(hostname: str) -> None:
    """Safely set hostname without shell injection.

    Args:
        hostname: Hostname to set

    Raises:
        SecurityError: If hostname is invalid
        subprocess.CalledProcessError: If hostname setting fails
    """
    if not hostname or len(hostname) > MAX_HOSTNAME_LENGTH:
        raise SecurityError(f"Invalid hostname length: {hostname}")

    # Basic hostname validation (RFC compliant)
    if not all(c in ALLOWED_HOSTNAME_CHARS for c in hostname):
        raise SecurityError(f"Invalid hostname characters: {hostname}")

    try:
        subprocess.run(
            ["hostname", hostname], check=True, capture_output=True, text=True
        )
        logger.info(f"Successfully set hostname to {hostname}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to set hostname: {e.stderr}")
        raise


def safe_make_mount_private() -> None:
    """Safely make root mount private.

    Raises:
        subprocess.CalledProcessError: If mount operation fails
    """
    try:
        subprocess.run(
            ["mount", "--make-private", "/"], check=True, capture_output=True, text=True
        )
        logger.info("Successfully made root mount private")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to make mount private: {e.stderr}")
        raise
