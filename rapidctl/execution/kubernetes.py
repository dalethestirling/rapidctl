import os
import json
import uuid
import time
from typing import List, Iterator, Dict

from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

from rapidctl.execution.base import ExecutionContext

class KubernetesExecutionContext(ExecutionContext):
    """
    ExecutionContext implementation for remote Kubernetes execution.
    Creates short-lived Jobs to execute commands and streams the pod logs.
    """
    
    def __init__(self, repo: str, command_path: str, namespace: str = "default"):
        """
        Initialize the Kubernetes context.
        
        Args:
            repo (str): The repository name (e.g., ghcr.io/namespace/tool).
            command_path (str): Path inside the container where scripts are located.
            namespace (str): The Kubernetes namespace to run jobs in.
        """
        self.repo = repo
        self.command_path = command_path
        self.namespace = namespace
        self.resolved_image = None
        
        # Load configuration (in-cluster or local kubeconfig)
        try:
            config.load_incluster_config()
        except config.config_exception.ConfigException:
            config.load_kube_config()
            
        self.batch_v1 = client.BatchV1Api()
        self.core_v1 = client.CoreV1Api()

    def ensure_readiness(self, version: str) -> None:
        """
        Ensures the requested image version is ready.
        For Kubernetes, we just set the image string.
        """
        self.resolved_image = f"{self.repo}:{version}"

    def _create_job_manifest(self, job_name: str, full_command: List[str]) -> client.V1Job:
        """Create the V1Job object."""
        container = client.V1Container(
            name="rapidctl-worker",
            image=self.resolved_image,
            command=full_command,
            image_pull_policy="IfNotPresent",
        )
        
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"job-name": job_name}),
            spec=client.V1PodSpec(restart_policy="Never", containers=[container])
        )
        
        spec = client.V1JobSpec(
            template=template,
            backoff_limit=0
        )
        
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=job_name),
            spec=spec
        )
        return job

    def run_command(self, sub_command: str, args: List[str]) -> Iterator[str]:
        """
        Execute a command in a Kubernetes Job.
        """        
        if not self.resolved_image:
            raise RuntimeError("Execution context not ready. Call ensure_readiness() first.")
            
        full_command_path = os.path.join(self.command_path, sub_command)
        full_command = [full_command_path] + args
        
        job_name = f"rapidctl-cmd-{uuid.uuid4().hex[:8]}"
        job = self._create_job_manifest(job_name, full_command)
        
        try:
            self.batch_v1.create_namespaced_job(namespace=self.namespace, body=job)
        except ApiException as e:
            yield f"Exception creating job: {e}\n"
            return

        # Wait for the pod to be created and start running/complete
        pod_name = None
        w = watch.Watch()
        for event in w.stream(self.core_v1.list_namespaced_pod, namespace=self.namespace, label_selector=f"job-name={job_name}"):
            pod = event['object']
            pod_name = pod.metadata.name
            if pod.status.phase in ['Running', 'Succeeded', 'Failed']:
                w.stop()
                break
                
        if not pod_name:
            yield "Failed to find pod for job.\n"
            return
            
        # Stream logs
        try:
            for line in self.core_v1.read_namespaced_pod_log(name=pod_name, namespace=self.namespace, follow=True, _preload_content=False):
                if isinstance(line, bytes):
                    yield line.decode('utf-8')
                else:
                    yield str(line)
        except ApiException as e:
            yield f"Error reading logs: {e}\n"
            
        # Cleanup
        try:
            self.batch_v1.delete_namespaced_job(
                name=job_name,
                namespace=self.namespace,
                propagation_policy="Background"
            )
        except ApiException:
            pass # Ignore cleanup errors

    def get_supported_commands(self) -> Dict[str, Dict]:
        """
        Discover subcommands by reading the commands manifest.
        For Kubernetes, we create a short-lived job to run `cat commands.json`.
        """
        if not self.resolved_image:
            raise RuntimeError("Execution context not ready. Call ensure_readiness() first.")
            
        base_path = os.path.dirname(self.command_path.rstrip('/'))
        json_path = os.path.join(base_path, "commands.json")
        
        job_name = f"rapidctl-discover-{uuid.uuid4().hex[:8]}"
        job = self._create_job_manifest(job_name, ["cat", json_path])
        
        try:
            self.batch_v1.create_namespaced_job(namespace=self.namespace, body=job)
            
            # Wait for pod
            pod_name = None
            w = watch.Watch()
            for event in w.stream(self.core_v1.list_namespaced_pod, namespace=self.namespace, label_selector=f"job-name={job_name}"):
                pod = event['object']
                pod_name = pod.metadata.name
                if pod.status.phase in ['Running', 'Succeeded', 'Failed']:
                    w.stop()
                    break
                    
            output_str = ""
            if pod_name:
                output = self.core_v1.read_namespaced_pod_log(name=pod_name, namespace=self.namespace, _preload_content=False)
                output_str = output.read().decode('utf-8')
                
            # Cleanup
            try:
                self.batch_v1.delete_namespaced_job(
                    name=job_name,
                    namespace=self.namespace,
                    propagation_policy="Background"
                )
            except ApiException:
                pass
                
            if output_str:
                return json.loads(output_str)
                
        except Exception:
            pass
            
        return {}
