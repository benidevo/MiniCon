"""Constants for MiniCon application."""

import os

# Default configuration values
DEFAULT_MEMORY_LIMIT = 250 * 1024 * 1024  # 250MB in bytes
DEFAULT_CPU_SHARES = 1024  # Default CPU shares for cgroups

# Base directories
DEFAULT_BASE_DIR = "/var/lib/minicon"
DEFAULT_BASE_IMAGE_PATH = "/var/lib/minicon/base"
DEFAULT_ROOTFS_DIR = "/var/lib/minicon/rootfs"
DEFAULT_REGISTRY_FILE = "containers.json"

# Configurable paths (can be overridden by environment variables)
MINICON_BASE_DIR = os.getenv("MINICON_BASE_DIR", DEFAULT_BASE_DIR)
MINICON_BASE_IMAGE = os.getenv("MINICON_BASE_IMAGE", DEFAULT_BASE_IMAGE_PATH)
MINICON_ROOTFS_DIR = os.getenv("MINICON_ROOTFS_DIR", DEFAULT_ROOTFS_DIR)
MINICON_REGISTRY_FILE = os.getenv("MINICON_REGISTRY_FILE", DEFAULT_REGISTRY_FILE)

# Memory and resource limits
MINICON_MEMORY_LIMIT = int(os.getenv("MINICON_MEMORY_LIMIT", str(DEFAULT_MEMORY_LIMIT)))

# Linux namespace flags (defined as constants for clarity)
CLONE_NEWNS = 0x00020000  # Mount namespace
CLONE_NEWUTS = 0x04000000  # UTS namespace
CLONE_NEWPID = 0x20000000  # PID namespace
CLONE_NEWUSER = 0x10000000  # User namespace

# Essential directories created in container rootfs
ESSENTIAL_DIRECTORIES = ["proc", "sys", "dev", "tmp", "etc", "bin", "lib", "home"]

# Dangerous commands blocked by security validation
DANGEROUS_COMMANDS = {
    "rm",
    "rmdir",
    "dd",
    "mkfs",
    "fdisk",
    "parted",
    "mount",
    "umount",
    "sudo",
    "su",
    "chmod",
    "chown",
}

# Container name validation
MAX_CONTAINER_NAME_LENGTH = 64
ALLOWED_CONTAINER_NAME_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
)

# Hostname validation
MAX_HOSTNAME_LENGTH = 253
ALLOWED_HOSTNAME_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-."
)

# Default safe path base for validation
DEFAULT_SAFE_PATH_BASE = MINICON_BASE_DIR

# Libc library paths for different architectures
LIBC_PATHS = [
    "libc.so.6",
    "/usr/lib/aarch64-linux-gnu/libc.so.6",
    "/lib/x86_64-linux-gnu/libc.so.6",
    "/usr/lib/libc.dylib",  # macOS
    "libc.dylib",  # macOS fallback
]

# Essential binary paths to copy to containers
ESSENTIAL_BINARY_PATHS = [
    ("/bin/sh", "/usr/bin/sh"),
    ("/bin/echo", "/usr/bin/echo"),
    ("/bin/cat", "/usr/bin/cat"),
    ("/bin/ls", "/usr/bin/ls"),
    ("/bin/bash", "/usr/bin/bash"),
]

# Container library directories
CONTAINER_LIB_DIRS = ["lib", "lib64", "usr/lib", "lib/aarch64-linux-gnu"]

# Essential system libraries to copy to containers
ESSENTIAL_SYSTEM_LIBS = [
    ("/lib/aarch64-linux-gnu/libc.so.6", "lib/aarch64-linux-gnu/libc.so.6"),
    ("/lib/ld-linux-aarch64.so.1", "lib/ld-linux-aarch64.so.1"),
    ("/usr/lib/aarch64-linux-gnu/libc.so.6", "lib/aarch64-linux-gnu/libc.so.6"),
]

# File permissions
EXECUTABLE_PERMISSION = 0o755

# System paths
PROC_PATH = "/proc"
