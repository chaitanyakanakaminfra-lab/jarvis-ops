import boto3
import structlog
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class LintQualityAgent(BaseAgent):
    agent_id   = "lint_quality"
    agent_name = "Lint & Code Quality Agent"

    async def _run(self, command: str) -> str:
        cmd = command.lower()
        try:
            if any(w in cmd for w in ["scan", "vulnerability", "cve", "security"]):
                return await self._run_security_scan()
            if any(w in cmd for w in ["image", "ecr", "container"]):
                return await self._check_image_quality()
            if any(w in cmd for w in ["config", "compliance", "policy"]):
                return await self._check_config_compliance()
            return await self._run_full_check()
        except Exception as e:
            return f"Code quality check failed: {str(e)}"

    async def _run_full_check(self) -> str:
        try:
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            total_critical = 0
            total_high = 0
            scanned = 0
            for repo in repos[:5]:
                try:
                    findings = ecr.describe_image_scan_findings(
                        repositoryName=repo["repositoryName"],
                        imageId={"imageTag": "latest"},
                    )
                    counts = findings.get("imageScanFindings", {}).get("findingSeverityCounts", {})
                    total_critical += counts.get("CRITICAL", 0)
                    total_high += counts.get("HIGH", 0)
                    scanned += 1
                except:
                    pass
            if total_critical > 0:
                return f"Code quality: {scanned} images scanned. Found {total_critical} critical, {total_high} high severity issues. Patching required!"
            return f"Code quality: {scanned} images scanned across {len(repos)} repos. No critical issues. {total_high} high severity findings to review."
        except Exception as e:
            return f"Quality check error: {str(e)}"

    async def _run_security_scan(self) -> str:
        try:
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            results = []
            for repo in repos[:5]:
                try:
                    findings = ecr.describe_image_scan_findings(
                        repositoryName=repo["repositoryName"],
                        imageId={"imageTag": "latest"},
                    )
                    counts = findings.get("imageScanFindings", {}).get("findingSeverityCounts", {})
                    critical = counts.get("CRITICAL", 0)
                    high = counts.get("HIGH", 0)
                    results.append(f"{repo['repositoryName']}: {critical}C/{high}H")
                except:
                    pass
            return f"Security scan results: {'; '.join(results) if results else 'No scan data available'}."
        except Exception as e:
            return f"Security scan error: {str(e)}"

    async def _check_image_quality(self) -> str:
        try:
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            untagged = 0
            for repo in repos:
                try:
                    images = ecr.describe_images(
                        repositoryName=repo["repositoryName"],
                        filter={"tagStatus": "UNTAGGED"}
                    )["imageDetails"]
                    untagged += len(images)
                except:
                    pass
            return f"Image quality: {len(repos)} repos checked. {untagged} untagged images found. Consider cleanup to reduce costs."
        except Exception as e:
            return f"Image quality error: {str(e)}"

    async def _check_config_compliance(self) -> str:
        try:
            ec2 = boto3.client("ec2", region_name="us-east-1")
            sgs = ec2.describe_security_groups()["SecurityGroups"]
            issues = sum(1 for sg in sgs for p in sg.get("IpPermissions", [])
                        for r in p.get("IpRanges", [])
                        if r.get("CidrIp") == "0.0.0.0/0" and p.get("FromPort") in [22, 3389])
            return f"Config compliance: {len(sgs)} security groups checked. {issues} compliance issues found."
        except Exception as e:
            return f"Compliance check error: {str(e)}"
