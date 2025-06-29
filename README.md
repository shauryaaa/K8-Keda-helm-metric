# Kubernetes Automation Script

This is a Python CLI script designed to automate common operations on a Kubernetes cluster, focusing on deploying applications with KEDA-driven autoscaling. It is built in a modular fashion to support reusability and clarity.

## Project Structure

```

Shaurya\Users\K8s_automation_script
├── k8s\_automation.py       \# Main script entry point (CLI)
├── cluster\_utils.py        \# Utility functions for Kubernetes cluster connection and shell commands
├── install\_utils.py        \# Utility functions for installing and verifying tools like KEDA
├── deployment\_utils.py     \# Utility functions for creating deployments, ScaledObjects, and checking their health
├── **init**.py             \# Marks the directory as a Python package (can be empty)
├── requirements.txt        \# Python dependencies
├── README.md               \# This documentation file
└── charts/                 \# Directory to hold your Helm charts
└── my-app-chart/       
├── Chart.yaml
├── values.yaml
└── templates/
├── deployment.yaml
└── service.yaml
└── scaledobject.yaml \# Your KEDA ScaledObject definition

````

## Prerequisites

Before running the script, ensure you have the following installed and configured:

1.  **Python 3.x:** (Recommended Python 3.8+)
    * [Download Python](https://www.python.org/downloads/)
2.  **`kubectl` CLI:** Configured to connect to your target Kubernetes cluster.
    * [Install kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
3.  **`helm` CLI:** Installed on your local machine.
    * [Install Helm](https://helm.sh/docs/intro/install/)
4.  **Python Dependencies:** Install the required Python libraries using pip:
    ```bash
    pip install -r requirements.txt
    ```
5.  **Your Application Helm Chart:** Place your application's Helm chart (e.g., `my-app-chart`) inside the `charts/` directory relative to `k8s_automation.py`. Ensure it includes your Deployment and ScaledObject definitions.

## Configuration

The script uses default values for KEDA and your application's deployment. You can customize these defaults in `k8s_automation.py` or override them directly via command-line arguments.

**Key Configuration Parameters (in `k8s_automation.py`):**

* `DEFAULT_KEDA_NAMESPACE`: Namespace for KEDA (default: `keda`)
* `DEFAULT_KEDA_CHART_VERSION`: KEDA Helm chart version (default: `2.17.2` - consider `2.16.0` if you faced the `unknown metric type` error)
* `DEFAULT_APP_RELEASE_NAME`: Helm release name for your application (default: `my-new-helm-app`)
* `DEFAULT_APP_CHART_PATH`: Path to your application's Helm chart (default: `charts/my-app-chart`)
* `DEFAULT_APP_NAMESPACE`: Namespace for your application (default: `default`)
* `DEFAULT_APP_DEPLOYMENT_NAME`: The name of the Deployment resource created by your chart (e.g., `my-new-helm-app-my-app-chart`)
* `DEFAULT_APP_SCALED_OBJECT_NAME`: The name of the ScaledObject resource created by your chart (e.g., `my-new-helm-app-my-app-chart-scaledobject`)

## Usage

Navigate to the directory containing `k8s_automation.py` in your terminal.

```bash
# Basic usage: Perform all actions (install KEDA, deploy app, check health)
python k8s_automation.py

# Perform only KEDA installation
python k8s_automation.py --action install-keda

# Deploy your application after KEDA is already installed
python k8s_automation.py --action deploy-app

# Check the health status of your deployment
python k8s_automation.py --action check-health

# Uninstall your application
python k8s_automation.py --action uninstall-app

# Uninstall KEDA
python k8s_automation.py --action uninstall-keda

# --- Overriding default configuration ---
# Example: Deploying to a different namespace with a specific KEDA version
python k8s_automation.py --action all \
    --keda-namespace my-keda-ns \
    --keda-version 2.16.0 \
    --app-namespace my-app-ns \
    --app-release-name my-custom-app-release \
    --app-chart-path ./my-custom-chart-path \
    --app-deployment-name my-custom-deploy \
    --app-scaled-object-name my-custom-scaledobject

# Get help on available arguments
python k8s_automation.py --help
````

## Health Status Details

The `check-health` action (and the `all` action) will provide:

  * Deployment replica status.
  * Deployment conditions.
  * Associated pod statuses and conditions.
  * Service endpoints linked to the application (if found).
  * Summary of the KEDA ScaledObject status (Ready/Active, Min/Max replicas, triggers).
  * **Important:** If the ScaledObject is not ready, it will attempt to fetch and display the latest KEDA operator logs to help diagnose issues (like the persistent "unknown metric type" error).

## Notes on Autoscaling (CPU Metric Error)

During development and testing of the CPU `Utilization` metric, a persistent error `error parsing cpu metadata: unknown metric type: , allowed values are 'Utilization' or 'AverageValue'` was encountered in the KEDA operator logs. This occurred despite the `ScaledObject` YAML being correctly configured. This suggests a deep-seated issue, possibly related to caching within the KEDA operator or specific interactions with the Kubernetes environment (e.g., Docker Desktop). The script will still attempt to configure CPU scaling as per the chart, but you should monitor the `ScaledObject` status and KEDA logs for this specific error. Trying KEDA version `2.16.0` might be a diagnostic step.
