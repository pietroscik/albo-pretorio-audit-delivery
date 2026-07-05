"""Model trainer. TODO: Migrate from scripts/train_model.py"""
import argparse

def main():
    parser = argparse.ArgumentParser(description="Train models")
    parser.add_argument("--base", default="albo_download")
    args = parser.parse_args()
    print("TODO: Implement model training")

if __name__ == "__main__":
    main()