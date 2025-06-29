import subprocess
from kubernetes import client, config
from tabulate import tabulate

def connect_to_cluster():
    """Connects to the Kubernetes cluster using kubectl's default config."""
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        print("Successfully connected to Kubernetes cluster.")
        return v1
    except config.ConfigException as e:
        print(f"Error connecting to Kubernetes cluster: {e}")
        print("Please ensure kubectl is configured correctly and can access the cluster.")
        return None

def get_cluster_summary():
    """Provides a summary of the Kubernetes cluster setup."""
    summary_data = []
    try:
        # Get Kubernetes version
        version_output = subprocess.run(['kubectl', 'version', '--short'], capture_output=True, text=True, check=True)
        version_lines = version_output.stdout.strip().split('\n')
        client_version = version_lines[0].replace('Client Version: ', '')
        server_version = version_lines[1].replace('Server Version: ', '')
        summary_data.append(["Kubernetes Client Version", client_version])
        summary_data.append(["Kubernetes Server Version", server_version])

        # Get nodes information
        api = client.CoreV1Api()
        nodes = api.list_node().items
        node_names = [node.metadata.name for node in nodes]
        summary_data.append(["Number of Nodes", len(nodes)])
        summary_data.append(["Node Names", ", ".join(node_names)])

        # Check namespaces
        namespaces = api.list_namespace().items
        namespace_names = [ns.metadata.name for ns in namespaces]
        summary_data.append(["Number of Namespaces", len(namespaces)])
        summary_data.append(["Namespaces", ", ".join(namespace_names[:5]) + ("..." if len(namespace_names) > 5 else "")])

        # Check Helm installation
        try:
            helm_version_output = subprocess.run(['helm', 'version', '--short'], capture_output=True, text=True, check=True)
            summary_data.append(["Helm Installed", "Yes"])
            summary_data.append(["Helm Version", helm_version_output.stdout.strip()])
        except (subprocess.CalledProcessError, FileNotFoundError):
            summary_data.append(["Helm Installed", "No"])
            summary_data.append(["Helm Version", "N/A"])

        # Check KEDA installation
        try:
            # Check for KEDA CRDs
            crd_output = subprocess.run(['kubectl', 'get', 'crd', 'scaledobjects.keda.sh'], capture_output=True, text=True)
            if "scaledobjects.keda.sh" in crd_output.stdout:
                summary_data.append(["KEDA Installed", "Yes"])
                # Check KEDA operator deployment
                keda_deployment_output = subprocess.run(['kubectl', 'get', 'deployment', '-n', 'keda', 'keda-operator'], capture_output=True, text=True)
                if "keda-operator" in keda_deployment_output.stdout:
                    summary_data.append(["KEDA Operator Running", "Yes"])
                else:
                    summary_data.append(["KEDA Operator Running", "No (Deployment not found)"])
            else:
                summary_data.append(["KEDA Installed", "No (CRD not found)"])
                summary_data.append(["KEDA Operator Running", "N/A"])
        except (subprocess.CalledProcessError, FileNotFoundError):
            summary_data.append(["KEDA Installed", "No (kubectl command failed)"])
            summary_data.append(["KEDA Operator Running", "N/A"])

        print("\n--- Kubernetes Cluster Summary ---")
        print(tabulate(summary_data, headers=["Metric", "Value"], tablefmt="grid"))
        print("----------------------------------\n")

    except Exception as e:
        print(f"Error getting cluster summary: {e}")