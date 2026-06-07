import boto3
import structlog
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class ComplianceAgent(BaseAgent):
    agent_id   = "compliance"
    agent_name = "Compliance Agent"

    async def _run(self, command: str) -> str:
        cmd = command.lower()
        try:
            if any(w in cmd for w in ["s3", "bucket", "storage"]):
                return await self._check_s3_compliance()
            if any(w in cmd for w in ["iam", "access", "permission"]):
                return await self._check_iam_compliance()
            if any(w in cmd for w in ["encryption", "encrypt"]):
                return await self._check_encryption()
            if any(w in cmd for w in ["tag", "tagging", "labels"]):
                return await self._check_tagging()
            return await self._get_compliance_overview()
        except Exception as e:
            return f"Compliance check failed: {str(e)}"

    async def _get_compliance_overview(self) -> str:
        try:
            checks = []
            score = 100
            ec2 = boto3.client("ec2", region_name="us-east-1")
            sgs = ec2.describe_security_groups()["SecurityGroups"]
            open_ports = sum(1 for sg in sgs for p in sg.get("IpPermissions", [])
                           for r in p.get("IpRanges", [])
                           if r.get("CidrIp") == "0.0.0.0/0" and p.get("FromPort") in [22, 3389])
            if open_ports:
                score -= 20
                checks.append(f"{open_ports} open admin ports")

            s3 = boto3.client("s3")
            buckets = s3.list_buckets()["Buckets"]
            unencrypted = 0
            for b in buckets[:5]:
                try:
                    s3.get_bucket_encryption(Bucket=b["Name"])
                except:
                    unencrypted += 1
            if unencrypted:
                score -= 10
                checks.append(f"{unencrypted} unencrypted buckets")

            status = "COMPLIANT" if score >= 80 else "NON-COMPLIANT"
            issues = f" Issues: {', '.join(checks)}." if checks else ""
            return f"Compliance score: {score}/100 ({status}).{issues} {len(sgs)} security groups, {len(buckets)} S3 buckets checked."
        except Exception as e:
            return f"Compliance overview error: {str(e)}"

    async def _check_s3_compliance(self) -> str:
        try:
            s3 = boto3.client("s3")
            buckets = s3.list_buckets()["Buckets"]
            issues = []
            for b in buckets:
                try:
                    s3.get_bucket_encryption(Bucket=b["Name"])
                except:
                    issues.append(f"{b['Name']}: no encryption")
            if issues:
                return f"S3 compliance: {len(issues)} buckets without encryption: {', '.join(issues[:3])}."
            return f"S3 compliance: All {len(buckets)} buckets are encrypted. Compliant."
        except Exception as e:
            return f"S3 compliance error: {str(e)}"

    async def _check_iam_compliance(self) -> str:
        try:
            iam = boto3.client("iam")
            users = iam.list_users()["Users"]
            no_mfa = []
            for user in users[:10]:
                devices = iam.list_mfa_devices(UserName=user["UserName"])["MFADevices"]
                if not devices:
                    no_mfa.append(user["UserName"])
            if no_mfa:
                return f"IAM compliance: {len(no_mfa)} users without MFA: {', '.join(no_mfa[:3])}. Enable MFA immediately."
            return f"IAM compliance: All {len(users)} users have MFA enabled. Compliant."
        except Exception as e:
            return f"IAM compliance error: {str(e)}"

    async def _check_encryption(self) -> str:
        try:
            ec2 = boto3.client("ec2", region_name="us-east-1")
            volumes = ec2.describe_volumes()["Volumes"]
            unencrypted = [v for v in volumes if not v.get("Encrypted", False)]
            s3 = boto3.client("s3")
            buckets = s3.list_buckets()["Buckets"]
            return f"Encryption check: {len(volumes)} EBS volumes ({len(unencrypted)} unencrypted), {len(buckets)} S3 buckets checked."
        except Exception as e:
            return f"Encryption check error: {str(e)}"

    async def _check_tagging(self) -> str:
        try:
            ec2 = boto3.client("ec2", region_name="us-east-1")
            instances = ec2.describe_instances()
            untagged = 0
            total = 0
            for r in instances["Reservations"]:
                for i in r["Instances"]:
                    total += 1
                    tags = {t["Key"]: t["Value"] for t in i.get("Tags", [])}
                    if "Name" not in tags or "Environment" not in tags:
                        untagged += 1
            return f"Tagging compliance: {total} EC2 instances checked. {untagged} missing required tags (Name/Environment)."
        except Exception as e:
            return f"Tagging check error: {str(e)}"
