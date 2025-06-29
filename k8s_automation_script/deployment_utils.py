from kubernetes import client, config
import os
import yaml
import time
import subprocess
import json
import tempfile
import logging

# Configure logging (basic setup, adjust as needed)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def create_keda_deployment(
    deployment_name: str,
    namespace: str,
    image: str,
    tag: str,
    cpu_request: str,
    cpu_limit: str,
    mem_request: str,
    mem_limit: str,
    container_port: int,
    min_replicas: int,
    max_replicas: int,
    scaling_metric_type: str,
    scaling_metric_value: str,
    event_source_config: dict
):
    """
    Creates a Kubernetes deployment with KEDA autoscaling using direct Kubernetes API calls.
    """
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    core_v1 = client.CoreV1Api()
    autoscaling_v1 = client.CustomObjectsApi() # For ScaledObject

    # Create Namespace if it doesn't exist
    try:
        core_v1.read_namespace(name=namespace)
    except client.ApiException as e:
        if e.status == 404:
            logging.info(f"Namespace '{namespace}' not found. Creating...")
            namespace_body = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
            core_v1.create_namespace(body=namespace_body)
            logging.info(f"Namespace '{namespace}' created.")
        else:
            raise

    # 1. Create Deployment
    deployment_manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": deployment_name,
            "namespace": namespace,
            "labels": {"app": deployment_name}
        },
        "spec": {
            "replicas": min_replicas,
            "selector": {"matchLabels": {"app": deployment_name}},
            "template": {
                "metadata": {"labels": {"app": deployment_name}},
                "spec": {
                    "containers": [
                        {
                            "name": deployment_name,
                            "image": f"{image}:{tag}",
                            "ports": [{"containerPort": container_port}],
                            "resources": {
                                "requests": {
                                    "cpu": cpu_request,
                                    "memory": mem_request
                                },
                                "limits": {
                                    "cpu": cpu_limit,
                                    "memory": mem_limit
                                }
                            }
                        }
                    ]
                }
            }
        }
    }

    try:
        logging.info(f"Creating deployment '{deployment_name}' in namespace '{namespace}'...")
        apps_v1.create_namespaced_deployment(body=deployment_manifest, namespace=namespace)
        logging.info("Deployment created successfully.")
    except client.ApiException as e:
        logging.error(f"Error creating deployment: {e}")
        return None

    # 2. Create ScaledObject (KEDA)
    scaled_object_manifest = {
        "apiVersion": "keda.sh/v1alpha1",
        "kind": "ScaledObject",
        "metadata": {
            "name": f"{deployment_name}-scaledobject",
            "namespace": namespace,
            "labels": {"deploymentName": deployment_name}
        },
        "spec": {
            "scaleTargetRef": {
                "kind": "Deployment",
                "name": deployment_name
            },
            "minReplicaCount": min_replicas,
            "maxReplicaCount": max_replicas,
            "triggers": [
                {
                    "type": scaling_metric_type,
                    "metadata": {
                        "value": str(scaling_metric_value), # Generic value
                        **event_source_config # Merge event source specific config
                    }
                }
            ]
        }
    }

    try:
        logging.info(f"Creating KEDA ScaledObject for '{deployment_name}'...")
        autoscaling_v1.create_namespaced_custom_object(
            group="keda.sh",
            version="v1alpha1",
            namespace=namespace,
            plural="scaledobjects",
            body=scaled_object_manifest
        )
        logging.info("ScaledObject created successfully.")
    except client.ApiException as e:
        logging.error(f"Error creating ScaledObject: {e}")
        # Clean up deployment if ScaledObject creation fails
        logging.info(f"Attempting to delete deployment '{deployment_name}' due to ScaledObject error...")
        try:
            apps_v1.delete_namespaced_deployment(name=deployment_name, namespace=namespace, body=client.V1DeleteOptions())
        except client.ApiException as cleanup_e:
            logging.error(f"Error cleaning up deployment: {cleanup_e}")
        return None

    # Get deployment details and endpoints
    try:
        deployment_status = apps_v1.read_namespaced_deployment_status(name=deployment_name, namespace=namespace)
        endpoints = []
        endpoints.append(f"Internal Port: {container_port}")

        logging.info(f"\n--- Deployment '{deployment_name}' Details ---")
        logging.info(f"Image: {image}:{tag}")
        logging.info(f"Namespace: {namespace}")
        logging.info(f"Replicas: {deployment_status.status.replicas}")
        logging.info(f"Available Replicas: {deployment_status.status.available_replicas}")
        logging.info(f"Endpoints: {', '.join(endpoints)}")
        logging.info("\n--- Scaling Configuration ---")
        logging.info(f"Min Replicas: {min_replicas}")
        logging.info(f"Max Replicas: {max_replicas}")
        logging.info(f"Scaling Metric Type: {scaling_metric_type}")
        logging.info(f"Scaling Metric Value: {scaling_metric_value}")
        logging.info(f"Event Source Configuration: {yaml.dump(event_source_config, default_flow_style=False)}")
        logging.info("------------------------------------------\n")

        return {
            "deployment_name": deployment_name,
            "namespace": namespace,
            "image": f"{image}:{tag}",
            "endpoints": endpoints,
            "scaling_config": {
                "min_replicas": min_replicas,
                "max_replicas": max_replicas,
                "metric_type": scaling_metric_type,
                "metric_value": scaling_metric_value,
                "event_source": event_source_config
            }
        }

    except client.ApiException as e:
        logging.error(f"Error retrieving deployment details: {e}")
        return None

def get_deployment_health_status(deployment_name: str, namespace: str):
    """
    Provides the health status of a given deployment.
    """
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()

    try: # Ensure all lines below this, until the 'except' block, are properly indented
        deployment = apps_v1.read_namespaced_deployment(name=deployment_name, namespace=namespace)
        status = deployment.status

        health_status = {
            "Deployment Name": deployment_name,
            "Namespace": namespace,
            "Ready Replicas": status.ready_replicas if status.ready_replicas is not None else 0,
            "Updated Replicas": status.updated_replicas if status.updated_replicas is not None else 0,
            "Available Replicas": status.available_replicas if status.available_replicas is not None else 0,
            "Total Replicas": status.replicas if status.replicas is not None else 0,
            "Conditions": []
        }

        for condition in status.conditions:
            health_status["Conditions"].append({
                "Type": condition.type,
                "Status": condition.status,
                "Reason": condition.reason,
                "Message": condition.message
            })

        # This is the line reported as 210 in the traceback.
        # Ensure it and all subsequent logging.info lines are consistently indented.
        logging.info(f"\n--- Health Status for Deployment '{deployment_name}' in '{namespace}' ---")
        logging.info(f"Ready Replicas: {health_status['Ready Replicas']}/{health_status['Total Replicas']}")
        logging.info(f"Updated Replicas: {health_status['Updated Replicas']}")
        logging.info(f"Available Replicas: {health_status['Available Replicas']}")
        logging.info("\nConditions:")
        if health_status["Conditions"]:
            for cond in health_status["Conditions"]:
                logging.info(f"  - Type: {cond['Type']}, Status: {cond['Status']}, Reason: {cond['Reason']}, Message: {cond['Message']}")
        else:
            logging.info("  No conditions reported.")
        logging.info("-------------------------------------------------------------------\n")

        return health_status

    except client.ApiException as e: # This 'except' must be at the same indentation level as 'try'
        if e.status == 404:
            logging.error(f"Deployment '{deployment_name}' not found in namespace '{namespace}'.")
        else:
            logging.error(f"Error getting deployment status: {e}")
        return None
    
def create_keda_deployment_with_helm(
    release_name: str, # Helm release name
    namespace: str,
    chart_path: str,   # Path to your Helm chart directory (e.g., "my-app-chart")
    image: str,
    tag: str,
    cpu_request: str,
    cpu_limit: str,
    mem_request: str,
    mem_limit: str,
    container_port: int,
    min_replicas: int,
    max_replicas: int,
    scaling_metric_type: str,
    scaling_metric_value: str,
    event_source_config: dict
):
    """
    Creates a Kubernetes deployment with KEDA autoscaling using a Helm chart.
    """
    config.load_kube_config()
    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api() # For status checks

    # Create Namespace if it doesn't exist
    try:
        core_v1.read_namespace(name=namespace)
    except client.ApiException as e:
        if e.status == 404:
            logging.info(f"Namespace '{namespace}' not found. Creating...")
            namespace_body = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
            core_v1.create_namespace(body=namespace_body)
            logging.info(f"Namespace '{namespace}' created.")
        else:
            raise

    # Prepare Helm values
    # IMPORTANT: These keys must match the structure expected by your Helm chart's values.yaml
    # and the templates after our previous modifications (e.g., kedaConfig, disabled autoscaling for HPA).
    helm_values = {
        "image": {
            "repository": image,
            "tag": tag
        },
        "service": {
            "type": "ClusterIP", # Added for NOTES.txt fix if needed, assuming default chart service type
            "port": container_port
        },
        "resources": {
            "requests": {
                "cpu": cpu_request,
                "memory": mem_request
            },
            "limits": {
                "cpu": cpu_limit,
                "memory": mem_limit
            }
        },
        # Native Kubernetes HPA Configuration (from Helm's default chart, disable this!)
        "autoscaling": {
            "enabled": False, # Set this to False to avoid conflict with KEDA
            # Default values from Helm's autoscaling block, even if not used, can be left here
            "minReplicas": 1,
            "maxReplicas": 100,
            "targetCPUUtilizationPercentage": 80
        },
        # KEDA-specific configuration (renamed from 'autoscaling' to avoid collision)
        "kedaConfig": {
            "enabled": True,
            "minReplicas": min_replicas,
            "maxReplicas": max_replicas,
            "metricType": scaling_metric_type,
            "metricValue": scaling_metric_value,
            "eventSourceConfig": event_source_config
        },
        "replicaCount": min_replicas, # Initial replica count for the deployment itself
        "serviceAccount": { # Added for serviceaccount.yaml fix if using default chart
            "create": True,
            "automount": True
        },
        "ingress": { # Added for ingress.yaml fix if using default chart
            "enabled": False,
            "className": "",
            "annotations": {},
            "hosts": [
                {
                    "host": "chart-example.local",
                    "paths": [
                        {
                            "path": "/",
                            "pathType": "ImplementationSpecific"
                        }
                    ]
                }
            ],
            "tls": []
        }
    }

    # Use tempfile.mkstemp for a robust, cross-platform temporary file
    fd = None # File descriptor
    temp_values_file_path = None # File path

    try:
        # Create a temporary file and get its file descriptor (fd) and path
        fd, temp_values_file_path = tempfile.mkstemp(suffix='.yaml')

        # Open the file using the file descriptor and write content
        with os.fdopen(fd, 'w') as temp_file:
            yaml_values = yaml.dump(helm_values, Dumper=yaml.SafeDumper)
            temp_file.write(yaml_values)
            # The file is automatically flushed and closed when exiting this 'with' block

        # Construct the Helm install command
        helm_install_command = [
            'helm', 'install', release_name, chart_path,
            '--namespace', namespace,
            '-f', temp_values_file_path, # Use the string path here
            '--wait' # Wait for pods to be ready
        ]
        # Execute the Helm command
        logging.info(f"Installing Helm chart '{chart_path}' as release '{release_name}' in namespace '{namespace}'...")
        logging.debug(f"Helm command: {' '.join(helm_install_command)}") # Log the full command
        result = subprocess.run(helm_install_command, capture_output=True, text=True, check=True)

        logging.info(f"Helm release '{release_name}' installed successfully.")
        logging.info(f"Helm stdout:\n{result.stdout}")
        if result.stderr:
            logging.warning(f"Helm stderr:\n{result.stderr}") # Use warning for stderr output

    except subprocess.CalledProcessError as e:
        logging.error(f"Error installing Helm release: {e.cmd}")
        logging.error(f"Error: {e.stderr}")
        raise # Re-raise the exception after logging
    except FileNotFoundError:
        logging.error("Error: 'helm' command not found. Please ensure Helm CLI is installed and in your PATH.")
        raise # Re-raise the exception after logging
    except Exception as e: # Catch all other unexpected exceptions
        logging.error(f"An unexpected error occurred during Helm installation: {e}")
        raise # Re-raise the exception after logging
    finally:
        # Ensure the temporary file is cleaned up
        if temp_values_file_path and os.path.exists(temp_values_file_path):
            os.remove(temp_values_file_path)

    # Now retrieve details after Helm install
    # The deployment name will be derived from the Helm full name (e.g., release-name-chart-name)
    # This assumes your Helm chart uses the common naming convention: {{ .Release.Name }}-{{ include "chart.name" . }}
    chart_name_from_path = os.path.basename(chart_path)
    deployment_name_in_k8s = f"{release_name}-{chart_name_from_path}"

    try:
        # Wait a bit for deployment to be fully available if '--wait' in helm install wasn't enough
        # Optional: Add a loop with retries here if needed for more robustness
        time.sleep(5) # Give K8s some time to sync after Helm reports success

        deployment_status = apps_v1.read_namespaced_deployment_status(name=deployment_name_in_k8s, namespace=namespace)
        endpoints = []
        endpoints.append(f"Internal Container Port: {container_port}")

        logging.info(f"\n--- Deployment '{deployment_name_in_k8s}' Details (via Helm Release '{release_name}') ---")
        logging.info(f"Image: {image}:{tag}")
        logging.info(f"Namespace: {namespace}")
        logging.info(f"Replicas: {deployment_status.status.replicas}")
        logging.info(f"Available Replicas: {deployment_status.status.available_replicas}")
        logging.info(f"Endpoints: {', '.join(endpoints)}")
        logging.info("\n--- Scaling Configuration ---")
        logging.info(f"Min Replicas: {min_replicas}")
        logging.info(f"Max Replicas: {max_replicas}")
        logging.info(f"Scaling Metric Type: {scaling_metric_type}")
        logging.info(f"Scaling Metric Value: {scaling_metric_value}")
        logging.info(f"Event Source Configuration: {yaml.dump(event_source_config, default_flow_style=False)}")
        logging.info("------------------------------------------\n")

        return {
            "helm_release_name": release_name,
            "deployment_name_in_k8s": deployment_name_in_k8s,
            "namespace": namespace,
            "image": f"{image}:{tag}",
            "endpoints": endpoints,
            "scaling_config": {
                "min_replicas": min_replicas,
                "max_replicas": max_replicas,
                "metric_type": scaling_metric_type,
                "metric_value": scaling_metric_value,
                "event_source": event_source_config
            }
        }

    except client.ApiException as e:
        logging.error(f"Error retrieving deployment details after Helm install: {e}")
        return None