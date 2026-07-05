"""Text sync. TODO: Migrate from scripts/sync_texts.py"""
import argparse

def main():
    parser = argparse.ArgumentParser(description="Sync texts")
    parser.add_argument("--base", default="albo_download")
    args = parser.parse_args()
    print("TODO: Implement text synchronization")

if __name__ == "__main__":
    main()