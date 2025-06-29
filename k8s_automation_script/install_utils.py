import subprocess
import time

def install_helm():
    """Installs Helm CLI and initializes it for the cluster."""
    print("Attempting to install Helm...")
    try:
        # Check if Helm is already installed
        subprocess.run(['helm', 'version'], check=True, capture_output=True)
        print("Helm is already installed.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Helm not found. Installing...")
        try:
            # Download and install Helm (for Linux/macOS)
            subprocess.run([
                'curl', '-fsSL', 'https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3',
                '|', 'bash'
            ], shell=True, check=True)
            print("Helm installed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing Helm: {e}")
            print("Please ensure you have curl installed and appropriate permissions.")
            return False
        except FileNotFoundError:
            print("Error: 'curl' command not found. Please install curl or install Helm manually.")
            return False

def install_keda():
    """Installs KEDA on the Kubernetes cluster using Helm."""
    print("Attempting to install KEDA...")
    try:
        # Add KEDA Helm repository
        subprocess.run(['helm', 'repo', 'add', 'kedacore', 'https://kedacore.github.io/charts'], check=True)
        subprocess.run(['helm', 'repo', 'update'], check=True)

        # Install KEDA
        subprocess.run([
            'helm', 'install', 'keda', 'kedacore/keda', '--namespace', 'keda',
            '--create-namespace'
        ], check=True)

        print("KEDA installation initiated. Verifying KEDA operator...")
        # Wait and verify KEDA operator deployment
        retries = 10
        while retries > 0:
            try:
                result = subprocess.run(
                    ['kubectl', 'get', 'deployment', '-n', 'keda', 'keda-operator', '-o', 'jsonpath="{.status.readyReplicas}"'],
                    capture_output=True, text=True, check=True
                )
                ready_replicas = int(result.stdout.strip().strip('"'))
                if ready_replicas >= 1:
                    print("KEDA operator is running successfully.")
                    return True
                else:
                    print(f"KEDA operator not ready yet. Retrying in 5 seconds... ({retries} attempts left)")
                    time.sleep(5)
                    retries -= 1
            except (subprocess.CalledProcessError, ValueError):
                print(f"Waiting for KEDA operator deployment... ({retries} attempts left)")
                time.sleep(5)
                retries -= 1
        print("KEDA operator did not become ready in time. Please check its status manually.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error installing KEDA: {e}")
        return False