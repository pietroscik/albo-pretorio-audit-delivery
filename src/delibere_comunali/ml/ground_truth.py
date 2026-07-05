"""Ground truth generator. TODO: Migrate from scripts/generate_ground_truth.py"""
import argparse

def main():
    parser = argparse.ArgumentParser(description="Generate ground truth")
    parser.add_argument("--base", default="albo_download")
    args = parser.parse_args()
    print("TODO: Implement ground truth generation")

if __name__ == "__main__":
    main()