"""Linked data export. TODO: Migrate from scripts/export_linked_data.py"""
import argparse

def main():
    parser = argparse.ArgumentParser(description="Export linked data")
    parser.add_argument("--base", default="albo_download")
    args = parser.parse_args()
    print("TODO: Implement linked data export")

if __name__ == "__main__":
    main()