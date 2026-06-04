"""
orchestrator/tools/cloud_tool.py
──────────────────────────────────
AWS cloud operations — ECR, EKS, Cost Explorer, CloudWatch.

Interview explanation:
  "The cloud tool wraps boto3 for all AWS operations. I use IRSA
   (IAM Roles for Service Accounts) so no AWS credentials are stored
   in the cluster — the pod assumes an IAM role automatically via
   the OIDC provider. On EC2, it uses the instance profile."
"""

import boto3
import structlog
from config.settings import get_settings

logger = structlog.get_logger(__name__)


class CloudTool:

    def __init__(self):
        self.settings = get_settings()
        self.region   = self.settings.aws_default_region
        self._ecr     = None
        self._eks     = None
        self._ce      = None
        self._cw      = None

    # ── ECR ───────────────────────────────────────────────────────────────────

    @property
    def ecr(self):
        if not self._ecr:
            self._ecr = boto3.client("ecr", region_name=self.region)
        return self._ecr

    async def get_ecr_login(self) -> dict:
        """Get ECR login token for docker login."""
        try:
            response = self.ecr.get_authorization_token()
            token = response["authorizationData"][0]
            logger.info("ecr.login_token_retrieved")
            return {
                "token":    token["authorizationToken"],
                "endpoint": token["proxyEndpoint"],
            }
        except Exception as e:
            logger.error("ecr.login_error", error=str(e))
            raise

    async def list_ecr_images(self, repo_name: str) -> list:
        """List images in an ECR repository."""
        try:
            response = self.ecr.list_images(repositoryName=repo_name)
            return response.get("imageIds", [])
        except Exception as e:
            logger.error("ecr.list_error", repo=repo_name, error=str(e))
            return []

    async def describe_ecr_repos(self) -> list:
        """List all Jarvis ECR repositories."""
        try:
            response = self.ecr.describe_repositories()
            repos = [
                r["repositoryName"]
                for r in response.get("repositories", [])
                if "jarvis" in r["repositoryName"]
            ]
            return repos
        except Exception as e:
            logger.error("ecr.describe_error", error=str(e))
            return []

    # ── EKS ───────────────────────────────────────────────────────────────────

    @property
    def eks(self):
        if not self._eks:
            self._eks = boto3.client("eks", region_name=self.region)
        return self._eks

    async def get_cluster_info(self, cluster_name: str = "jarvis-cluster") -> dict:
        """Get EKS cluster status."""
        try:
            response = self.eks.describe_cluster(name=cluster_name)
            cluster  = response["cluster"]
            return {
                "name":     cluster["name"],
                "status":   cluster["status"],
                "version":  cluster["version"],
                "endpoint": cluster["endpoint"],
            }
        except Exception as e:
            logger.error("eks.describe_error", error=str(e))
            return {"name": cluster_name, "status": "unknown", "error": str(e)}

    async def list_nodegroups(self, cluster_name: str = "jarvis-cluster") -> list:
        """List EKS node groups."""
        try:
            response = self.eks.list_nodegroups(clusterName=cluster_name)
            return response.get("nodegroups", [])
        except Exception as e:
            logger.error("eks.nodegroups_error", error=str(e))
            return []

    # ── Cost Explorer ─────────────────────────────────────────────────────────

    @property
    def ce(self):
        if not self._ce:
            self._ce = boto3.client("ce", region_name="us-east-1")
        return self._ce

    async def get_monthly_cost(self) -> dict:
        """Get current month AWS spend."""
        from datetime import datetime, date
        try:
            today      = date.today()
            start_date = today.replace(day=1).strftime("%Y-%m-%d")
            end_date   = today.strftime("%Y-%m-%d")

            response = self.ce.get_cost_and_usage(
                TimePeriod={"Start": start_date, "End": end_date},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
            )
            amount = float(
                response["ResultsByTime"][0]["Total"]["UnblendedCost"]["Amount"]
            )
            logger.info("cost.monthly_retrieved", amount=amount)
            return {
                "amount":     round(amount, 2),
                "currency":   "USD",
                "period":     f"{start_date} to {end_date}",
            }
        except Exception as e:
            logger.error("cost.monthly_error", error=str(e))
            return {"amount": 0, "currency": "USD", "error": str(e)}

    async def get_cost_by_service(self) -> list:
        """Get cost breakdown by AWS service."""
        from datetime import date
        try:
            today      = date.today()
            start_date = today.replace(day=1).strftime("%Y-%m-%d")
            end_date   = today.strftime("%Y-%m-%d")

            response = self.ce.get_cost_and_usage(
                TimePeriod={"Start": start_date, "End": end_date},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )
            services = []
            for group in response["ResultsByTime"][0]["Groups"]:
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                if amount > 0.01:
                    services.append({
                        "service": group["Keys"][0],
                        "cost":    round(amount, 2),
                    })
            return sorted(services, key=lambda x: x["cost"], reverse=True)
        except Exception as e:
            logger.error("cost.by_service_error", error=str(e))
            return []

    # ── CloudWatch ────────────────────────────────────────────────────────────

    @property
    def cw(self):
        if not self._cw:
            self._cw = boto3.client("cloudwatch", region_name=self.region)
        return self._cw

    async def get_alarms(self, state: str = "ALARM") -> list:
        """Get CloudWatch alarms in a given state."""
        try:
            response = self.cw.describe_alarms(StateValue=state)
            alarms = [
                {
                    "name":        a["AlarmName"],
                    "state":       a["StateValue"],
                    "reason":      a["StateReason"],
                    "metric":      a["MetricName"],
                }
                for a in response.get("MetricAlarms", [])
            ]
            logger.info("cloudwatch.alarms_retrieved", count=len(alarms))
            return alarms
        except Exception as e:
            logger.error("cloudwatch.alarms_error", error=str(e))
            return []
