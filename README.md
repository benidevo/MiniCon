# MiniCon

**MiniCon** is a lightweight container implementation in Python that demonstrates core virtualization concepts from ["Operating Systems: Three Easy Pieces" by Remzi H. Arpaci-Dusseau and Andrea C. Arpaci-Dusseau](https://pages.cs.wisc.edu/~remzi/OSTEP/). This project is designed for **educational purposes only** to help understand the underlying mechanisms of containers.

## ⚠️ Work in Progress

This project is currently under active development and is not intended for production use. Many core features are still being implemented.

## Overview

MiniCon provides a minimal container runtime that focuses on:

- Process isolation using Linux namespaces
- Filesystem isolation with mount namespaces
- Resource constraints using cgroups
- Simple container lifecycle management

## Educational Objectives

This project aims to provide hands-on experience with:

- PID namespace isolation
- Mount namespace isolation
- UTS namespace isolation
- Filesystem containerization
- Basic resource limiting
- Container state management

## Requirements

- Linux-based system (MiniCon is NOT cross-platform and works ONLY on Linux)
- Python 3.11+
- Root privileges (for namespace operations)

## Development

```bash
# Setup the development environment
make setup-dev

# Run formatter and linter
make check-all

# Run tests
make test
```

## Status

- [x] Project structure
- [x] Container model and registry
- [x] Namespace isolation implementations
- [x] Resource constraints
- [x] Container filesystem setup
- [x] Command-line interface
- [ ] Demo application (Python HTTP server)

## Important Notes

This project is inspired by the concepts presented in ["Operating Systems: Three Easy Pieces" by Remzi H. Arpaci-Dusseau and Andrea C. Arpaci-Dusseau](https://pages.cs.wisc.edu/~remzi/OSTEP/). It is not intended for production use and lacks many security features present in production container runtimes.

**Platform Limitation:** MiniCon relies heavily on Linux-specific kernel features such as namespaces and cgroups. It is NOT cross-platform and will only work on Linux systems.
