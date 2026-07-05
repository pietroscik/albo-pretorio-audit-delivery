"""Text cleaner. TODO: Migrate from scripts/clean_texts.py"""
import argparse

def main():
    parser = argparse.ArgumentParser(description="Clean texts")
    parser.add_argument("--base", default="albo_download")
    args = parser.parse_args()
    print("TODO: Implement text cleaning")

if __name__ == "__main__":
    main()