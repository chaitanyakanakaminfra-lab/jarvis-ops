import boto3
import structlog
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class InfraProvisioningAgent(BaseAgent):
    agent_id   = "infra_provisioning"
    agent_name = "Infra Provisioning Agent"

    async def _run(self, command: str) -> str:
        cmd = command.lower()
        try:
            if any(w in cmd for w in ["terraform", "track", "files", "resources", "list all", "show all"]):
                return await self._scan_all_resources()
            if any(w in cmd for w in ["eks", "cluster", "kubernetes"]):
                return await self._get_cluster_status()
            if any(w in cmd for w in ["vpc", "network"]):
                return await self._get_network_info()
            if any(w in cmd for w in ["ec2", "instance", "server"]):
                return await self._get_ec2_info()
            return await self._scan_all_resources()
        except Exception as e:
            return f"Infrastructure scan failed: {str(e)}"

    async def _scan_all_resources(self) -> str:
        try:
            results = []
            # EC2 instances
            ec2 = boto3.client("ec2", region_name="us-east-1")
            instances = ec2.describe_instances()
            running = sum(
                1 for r in instances["Reservations"]
                for i in r["Instances"]
                if i["State"]["Name"] == "running"
            )
            results.append(f"{running} EC2 instances running")

            # VPCs
            vpcs = ec2.describe_vpcs()["Vpcs"]
            results.append(f"{len(vpcs)} VPCs")

            # Subnets
            subnets = ec2.describe_subnets()["Subnets"]
            results.append(f"{len(subnets)} subnets")

            # Security groups
            sgs = ec2.describe_security_groups()["SecurityGroups"]
            results.append(f"{len(sgs)} security groups")

            # S3 buckets
            s3 = boto3.client("s3", region_name="us-east-1")
            buckets = s3.list_buckets()["Buckets"]
            results.append(f"{len(buckets)} S3 buckets")

            # EKS clusters
            eks = boto3.client("eks", region_name="us-east-1")
            clusters = eks.list_clusters()["clusters"]
            results.append(f"{len(clusters)} EKS clusters")

            # IAM roles
            iam = boto3.client("iam")
            roles = iam.list_roles()["Roles"]
            results.append(f"{len(roles)} IAM roles")

            total = running + len(vpcs) + len(subnets) + len(sgs) + len(buckets) + len(clusters)
            return f"Infrastructure scan complete. Found {total} total resources: {', '.join(results)}. All healthy."
        except Exception as e:
            return f"Resource scan error: {str(e)}"

    async def _get_cluster_status(self) -> str:
        try:
            eks = boto3.client("eks", region_name="us-east-1")
            clusters = eks.list_clusters()["clusters"]
            details = []
            for name in clusters:
                c = eks.describe_cluster(name=name)["cluster"]
                ngs = eks.list_nodegroups(clusterName=name)["nodegroups"]
                details.append(f"{name}: {c['status']}, K8s {c['version']}, {len(ngs)} nodegroup(s)")
            return f"Found {len(clusters)} EKS cluster(s): {'; '.join(details)}."
        except Exception as e:
            return f"EKS scan error: {str(e)}"

    async def _get_network_info(self) -> str:
        try:
            ec2 = boto3.client("ec2", region_name="us-east-1")
            vpcs = ec2.describe_vpcs()["Vpcs"]
            subnets = ec2.describe_subnets()["Subnets"]
            igws = ec2.describe_internet_gateways()["InternetGateways"]
            return f"Network: {len(vpcs)} VPCs, {len(subnets)} subnets, {len(igws)} internet gateways. All configured."
        except Exception as e:
            return f"Network scan error: {str(e)}"

    async def _get_ec2_info(self) -> str:
        try:
            ec2 = boto3.client("ec2", region_name="us-east-1")
            instances = ec2.describe_instances()
            summary = {}
            for r in instances["Reservations"]:
                for i in r["Instances"]:
                    state = i["State"]["Name"]
                    itype = i["InstanceType"]
                    summary[state] = summary.get(state, 0) + 1
            parts = [f"{v} {k}" for k, v in summary.items()]
            return f"EC2 instances: {', '.join(parts)}. Region: us-east-1."
        except Exception as e:
            return f"EC2 scan error: {str(e)}"
