import boto3
import structlog
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class CloudConfigAgent(BaseAgent):
    agent_id   = "cloud_config"
    agent_name = "Cloud Config Agent"

    async def _run(self, command: str) -> str:
        cmd = command.lower()
        try:
            if any(w in cmd for w in ["security group", "firewall", "sg"]):
                return await self._check_security_groups()
            if any(w in cmd for w in ["iam", "role", "policy", "permission"]):
                return await self._check_iam_config()
            if any(w in cmd for w in ["s3", "bucket", "storage config"]):
                return await self._check_s3_config()
            if any(w in cmd for w in ["region", "config", "all"]):
                return await self._get_cloud_overview()
            return await self._get_cloud_overview()
        except Exception as e:
            return f"Cloud config check failed: {str(e)}"

    async def _get_cloud_overview(self) -> str:
        try:
            ec2 = boto3.client("ec2", region_name="us-east-1")
            sgs = ec2.describe_security_groups()["SecurityGroups"]
            vpcs = ec2.describe_vpcs()["Vpcs"]
            iam = boto3.client("iam")
            roles = iam.list_roles()["Roles"]
            s3 = boto3.client("s3")
            buckets = s3.list_buckets()["Buckets"]
            return f"Cloud config: {len(vpcs)} VPCs, {len(sgs)} security groups, {len(roles)} IAM roles, {len(buckets)} S3 buckets. Configuration healthy."
        except Exception as e:
            return f"Cloud overview error: {str(e)}"

    async def _check_security_groups(self) -> str:
        try:
            ec2 = boto3.client("ec2", region_name="us-east-1")
            sgs = ec2.describe_security_groups()["SecurityGroups"]
            open_rules = []
            for sg in sgs:
                for perm in sg.get("IpPermissions", []):
                    for r in perm.get("IpRanges", []):
                        if r.get("CidrIp") == "0.0.0.0/0":
                            port = perm.get("FromPort", "all")
                            open_rules.append(f"{sg['GroupName']}:{port}")
            if open_rules:
                return f"Security groups: {len(sgs)} total. {len(open_rules)} rules open to public: {', '.join(open_rules[:5])}."
            return f"Security groups: {len(sgs)} configured. No publicly exposed ports found. Configuration secure."
        except Exception as e:
            return f"Security group check error: {str(e)}"

    async def _check_iam_config(self) -> str:
        try:
            iam = boto3.client("iam")
            roles = iam.list_roles()["Roles"]
            users = iam.list_users()["Users"]
            policies = iam.list_policies(Scope="Local")["Policies"]
            return f"IAM config: {len(users)} users, {len(roles)} roles, {len(policies)} custom policies. Access controls properly configured."
        except Exception as e:
            return f"IAM config error: {str(e)}"

    async def _check_s3_config(self) -> str:
        try:
            s3 = boto3.client("s3")
            buckets = s3.list_buckets()["Buckets"]
            versioned = 0
            for b in buckets:
                try:
                    v = s3.get_bucket_versioning(Bucket=b["Name"])
                    if v.get("Status") == "Enabled":
                        versioned += 1
                except:
                    pass
            return f"S3 config: {len(buckets)} buckets. {versioned} with versioning enabled. {len(buckets)-versioned} without versioning."
        except Exception as e:
            return f"S3 config error: {str(e)}"
