import boto3
import structlog
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class SecurityScanningAgent(BaseAgent):
    agent_id   = "security_scanning"
    agent_name = "Security Scanning Agent"

    async def _run(self, command: str) -> str:
        cmd = command.lower()
        try:
            if any(w in cmd for w in ["iam", "role", "permission", "access"]):
                return await self._check_iam()
            if any(w in cmd for w in ["security group", "firewall", "port", "open"]):
                return await self._check_security_groups()
            if any(w in cmd for w in ["s3", "bucket", "public"]):
                return await self._check_s3_security()
            if any(w in cmd for w in ["cve", "vulnerability", "ecr", "image"]):
                return await self._check_ecr_vulnerabilities()
            return await self._full_security_scan()
        except Exception as e:
            return f"Security scan failed: {str(e)}"

    async def _full_security_scan(self) -> str:
        try:
            issues = []
            ec2 = boto3.client("ec2", region_name="us-east-1")
            sgs = ec2.describe_security_groups()["SecurityGroups"]
            open_ssh = [sg for sg in sgs for p in sg.get("IpPermissions", [])
                       if p.get("FromPort") == 22
                       for r in p.get("IpRanges", [])
                       if r.get("CidrIp") == "0.0.0.0/0"]
            if open_ssh:
                issues.append(f"{len(open_ssh)} security group(s) with SSH open to world")

            s3 = boto3.client("s3", region_name="us-east-1")
            buckets = s3.list_buckets()["Buckets"]
            public_buckets = 0
            for b in buckets[:5]:
                try:
                    acl = s3.get_bucket_acl(Bucket=b["Name"])
                    for grant in acl["Grants"]:
                        if "AllUsers" in grant.get("Grantee", {}).get("URI", ""):
                            public_buckets += 1
                except:
                    pass
            if public_buckets:
                issues.append(f"{public_buckets} public S3 bucket(s) found")

            if issues:
                return f"Security scan complete. Issues found: {'; '.join(issues)}. Immediate action recommended."
            return f"Security scan complete. Checked {len(sgs)} security groups and {len(buckets)} S3 buckets. No critical issues found."
        except Exception as e:
            return f"Security scan error: {str(e)}"

    async def _check_iam(self) -> str:
        try:
            iam = boto3.client("iam")
            users = iam.list_users()["Users"]
            roles = iam.list_roles()["Roles"]
            mfa_disabled = []
            for user in users[:10]:
                devices = iam.list_mfa_devices(UserName=user["UserName"])["MFADevices"]
                if not devices:
                    mfa_disabled.append(user["UserName"])
            if mfa_disabled:
                return f"IAM check: {len(users)} users, {len(roles)} roles. Warning: {len(mfa_disabled)} user(s) without MFA: {', '.join(mfa_disabled[:3])}."
            return f"IAM check: {len(users)} users, {len(roles)} roles. All users have MFA enabled."
        except Exception as e:
            return f"IAM check error: {str(e)}"

    async def _check_security_groups(self) -> str:
        try:
            ec2 = boto3.client("ec2", region_name="us-east-1")
            sgs = ec2.describe_security_groups()["SecurityGroups"]
            issues = []
            for sg in sgs:
                for perm in sg.get("IpPermissions", []):
                    for r in perm.get("IpRanges", []):
                        if r.get("CidrIp") == "0.0.0.0/0":
                            port = perm.get("FromPort", "all")
                            if port in [22, 3389, 0]:
                                issues.append(f"{sg['GroupName']} port {port}")
            if issues:
                return f"Security group issues: {'; '.join(issues[:5])}. Review and restrict access."
            return f"Checked {len(sgs)} security groups. No critical open ports found."
        except Exception as e:
            return f"Security group check error: {str(e)}"

    async def _check_s3_security(self) -> str:
        try:
            s3 = boto3.client("s3", region_name="us-east-1")
            buckets = s3.list_buckets()["Buckets"]
            unencrypted = []
            for b in buckets:
                try:
                    enc = s3.get_bucket_encryption(Bucket=b["Name"])
                except:
                    unencrypted.append(b["Name"])
            if unencrypted:
                return f"S3 security: {len(buckets)} buckets. {len(unencrypted)} without encryption: {', '.join(unencrypted[:3])}."
            return f"S3 security: All {len(buckets)} buckets have encryption enabled."
        except Exception as e:
            return f"S3 security check error: {str(e)}"

    async def _check_ecr_vulnerabilities(self) -> str:
        try:
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            total_critical = 0
            scanned = 0
            for repo in repos:
                try:
                    findings = ecr.describe_image_scan_findings(
                        repositoryName=repo["repositoryName"],
                        imageId={"imageTag": "latest"},
                    )
                    counts = findings.get("imageScanFindings", {}).get("findingSeverityCounts", {})
                    total_critical += counts.get("CRITICAL", 0)
                    scanned += 1
                except:
                    pass
            if total_critical > 0:
                return f"ECR scan: {scanned} images scanned. Found {total_critical} critical CVEs! Immediate patching required."
            return f"ECR scan: {scanned} images scanned across {len(repos)} repositories. No critical vulnerabilities found."
        except Exception as e:
            return f"ECR scan error: {str(e)}"
