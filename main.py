#!/usr/bin/env python3
"""
FAT Recovery Tool - Main Entry Point
Công cụ khôi phục FAT - Điểm vào chính
"""

import sys
from cli import FATRecoveryCLI


def main():
    """Hàm main để chạy công cụ phân tích FAT"""
    cli = FATRecoveryCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
