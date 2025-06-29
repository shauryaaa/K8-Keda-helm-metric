import click
import json
import yaml

from cluster_utils import connect_to_cluster, get_cluster_summary
from install_utils import install_helm, install_keda
# from deployment_utils import create_keda_deployment, get_deployment_health_status

@click.group()
def cli():
    """A CLI tool to automate operations on a Kubernetes cluster with KEDA."""
    pass

@cli.command()
def setup_cluster():
    """Connects to the cluster, installs Helm, KEDA, and provides a summary."""
    click.echo("--- Setting up Kubernetes Cluster ---")
    api_client = connect_to_cluster()
    if api_client:
        click.echo("Cluster connection successful.")
        if install_helm():
            click.echo("Helm installation successful.")
        else:
            click.echo("Helm installation failed. Aborting KEDA installation.")
            return

        if install_keda():
            click.echo("KEDA installation successful.")
        else:
            click.echo("KEDA installation failed.")
            return

        get_cluster_summary()
    else:
        click.echo("Failed to connect to the cluster. Please check your kubectl configuration.")

@cli.command()
@click.option('--name', required=True, help='Name of the deployment.')
@click.option('--namespace', default='default', help='Namespace for the deployment.')
@click.option('--image', required=True, help='Docker image name (e.g., nginx).')
@click.option('--tag', default='latest', help='Docker image tag (e.g., latest).')
@click.option('--cpu-req', default='100m', help='CPU request (e.g., 100m).')
@click.option('--cpu-limit', default='200m', help='CPU limit (e.g., 200m).')
@click.option('--mem-req', default='128Mi', help='Memory request (e.g., 128Mi).')
@click.option('--mem-limit', default='256Mi', help='Memory limit (e.g., 256Mi).')
@click.option('--port', type=int, default=80, help='Container port to expose.')
@click.option('--min-replicas', type=int, default=1, help='Minimum replicas for autoscaling.')
@click.option('--max-replicas', type=int, default=10, help='Maximum replicas for autoscaling.')
@click.option('--scaling-metric-type', required=True, help='Type of KEDA metric (e.g., cpu, memory, kafka).')
@click.option('--scaling-metric-value', required=True, help='Target value for the scaling metric.')
@click.option('--event-source-config', help='JSON string for KEDA event source metadata (e.g., \'{"topic": "my-topic", "broker": "kafka-broker:9092"}\').')
def create_deployment_old(
    name, namespace, image, tag, cpu_req, cpu_limit, mem_req, mem_limit,
    port, min_replicas, max_replicas, scaling_metric_type, scaling_metric_value, event_source_config
):
    """
    Creates a KEDA-enabled Kubernetes deployment.
    Example:
    python k8s_automation.py create-deployment --name my-app --image my-repo/my-image --scaling-metric-type kafka --scaling-metric-value 10 --event-source-config '{"topic":"my-topic", "broker":"kafka-service:9092"}'
    """
    click.echo(f"--- Creating KEDA-enabled Deployment: {name} ---")

    parsed_event_source_config = {}
    if event_source_config:
        try:
            parsed_event_source_config = json.loads(event_source_config)
        except json.JSONDecodeError as e:
            click.echo(f"Error parsing event-source-config JSON: {e}")
            return

    deployment_details = create_keda_deployment(
        deployment_name=name,
        namespace=namespace,
        image=image,
        tag=tag,
        cpu_request=cpu_req,
        cpu_limit=cpu_limit,
        mem_request=mem_req,
        mem_limit=mem_limit,
        container_port=port,
        min_replicas=min_replicas,
        max_replicas=max_replicas,
        scaling_metric_type=scaling_metric_type,
        scaling_metric_value=scaling_metric_value,
        event_source_config=parsed_event_source_config
    )

    if deployment_details:
        click.echo("\nDeployment created successfully with the following details:")
        click.echo(yaml.dump(deployment_details, default_flow_style=False))
    else:
        click.echo("Failed to create deployment.")

@cli.command()
@click.option('--name', required=True, help='Name of the deployment.')
@click.option('--namespace', default='default', help='Namespace of the deployment.')
def get_status(name, namespace):
    """Provides the health status for a given deployment."""
    click.echo(f"--- Getting Health Status for Deployment: {name} ---")
    status = get_deployment_health_status(deployment_name=name, namespace=namespace)
    if not status:
        click.echo(f"Could not retrieve status for deployment '{name}' in namespace '{namespace}'.")

from deployment_utils import create_keda_deployment_with_helm, get_deployment_health_status # Update import
@cli.command()
@click.option('--name', required=True, help='Name of the Helm release (and base for deployment name).')
@click.option('--namespace', default='default', help='Namespace for the deployment.') # <--- THIS LINE IS CRUCIAL
@click.option('--chart-path', default=r'C:\Users\shaurya\k8s_automation_script\charts\my-app-chart', help='Path to the Helm chart for the deployment.')
# @click.option('--chart-path', default=r'..\charts\my-app-chart', help='Path to the Helm chart for the deployment.')
@click.option('--image', required=True, help='Docker image name (e.g., nginx).') # <--- THIS LINE IS CRUCIAL
@click.option('--tag', default='latest', help='Docker image tag (e.g., latest).')
@click.option('--cpu-req', default='100m', help='CPU request (e.g, 100m).')
@click.option('--cpu-limit', default='200m', help='CPU limit (e.g., 200m).')
@click.option('--mem-req', default='128Mi', help='Memory request (e.g   , 128Mi).')
@click.option('--mem-limit', default='256Mi', help='Memory limit (e.g., 256Mi).')
@click.option('--port', type=int, default=80, help='Container port to expose.') # <--- THIS LINE IS CRUCIAL
@click.option('--min-replicas', type=int, default=1, help='Minimum replicas for autoscaling.')
@click.option('--max-replicas', type=int, default=10, help='Maximum replicas for autoscaling.')
@click.option('--scaling-metric-type', required=True, help='Type of KEDA metric (e.g., cpu, memory, kafka).')
@click.option('--scaling-metric-value', required=True, help='Target valuea for the scaling metric.')
@click.option('--event-source-config', help='JSON string for KEDA event source metadata (e.g., \'{"topic": "my-topic", "broker": "kafka-broker:9092"}\').')
# ... other options ...
def create_deployment(
    name, namespace, chart_path, image, tag, cpu_req, cpu_limit, mem_req, mem_limit,
    port, min_replicas, max_replicas, scaling_metric_type, scaling_metric_value, event_source_config
):
    """
    Creates a KEDA-enabled Kubernetes deployment using a Helm chart.
    Example:
    python k8s_automation.py create-deployment --name my-app --chart-path ./my-app-chart --image my-repo/my-image --scaling-metric-type kafka --scaling-metric-value 10 --event-source-config '{"topic":"my-topic", "broker":"kafka-service:9092"}'
    """
    click.echo(f"--- Creating KEDA-enabled Deployment via Helm: {name} ---")

    parsed_event_source_config = {}
    if event_source_config:
        try:
            parsed_event_source_config = json.loads(event_source_config)
        except json.JSONDecodeError as e:
            click.echo(f"Error parsing event-source-config JSON: {e}")
            return

    deployment_details = create_keda_deployment_with_helm( # Call the new function
        release_name=name,
        namespace=namespace,
        chart_path=chart_path,
        image=image,
        tag=tag,
        cpu_request=cpu_req,
        cpu_limit=cpu_limit,
        mem_request=mem_req,
        mem_limit=mem_limit,
        container_port=port,
        min_replicas=min_replicas,
        max_replicas=max_replicas,
        scaling_metric_type=scaling_metric_type,
        scaling_metric_value=scaling_metric_value,
        event_source_config=parsed_event_source_config
    )

    if deployment_details:
        click.echo("\nDeployment created successfully with the following details:")
        click.echo(yaml.dump(deployment_details, default_flow_style=False))
    else:
        click.echo("Failed to create deployment.")

if __name__ == '__main__':
    cli()