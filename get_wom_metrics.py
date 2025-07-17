import requests
import json

def get_wom_metrics():
    """Fetch and print all available WOM metrics from the WiseOldMan API."""
    url = "https://api.wiseoldman.net/metrics"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()

            # Print all metric categories
            for category, metrics in data.items():
                print(f"\n{category.upper()} = [")
                for i, metric in enumerate(sorted(metrics)):
                    end = "," if i < len(metrics) - 1 else ""
                    print(f'    "{metric}"{end}')
                print("]")
            print("\nSummary:")
            for category, metrics in data.items():
                print(f"{category.title()}: {len(metrics)}")
        else:
            print(f"Error: HTTP {response.status_code}")
    except Exception as e:
        print(f"Error fetching metrics: {e}")

if __name__ == "__main__":
    get_wom_metrics() 