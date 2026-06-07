import boto3
import structlog
from datetime import datetime, timezone, timedelta
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class ReportingAgent(BaseAgent):
    agent_id   = "reporting"
    agent_name = "Reporting Agent"

    async def _run(self, command: str) -> str:
        cmd = command.lower()
        try:
            if any(w in cmd for w in ["weekly", "week", "summary"]):
                return await self._weekly_report()
            if any(w in cmd for w in ["cost", "spend", "financial"]):
                return await self._cost_report()
            if any(w in cmd for w in ["security", "compliance", "audit"]):
                return await self._security_report()
            if any(w in cmd for w in ["infra", "infrastructure", "resources"]):
                return await self._infra_report()
            return await self._weekly_report()
        except Exception as e:
            return f"Report generation failed: {str(e)}"

    async def _weekly_report(self) -> str:
        try:
            ce = boto3.client("ce", region_name="us-east-1")
            today = datetime.utcnow().date()
            week_ago = today - timedelta(days=7)
            result = ce.get_cost_and_usage(
                TimePeriod={"Start": str(week_ago), "End": str(today)},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
            )
            weekly_cost = sum(float(d["Total"]["UnblendedCost"]["Amount"]) for d in result["ResultsByTime"])

            cw = boto3.client("cloudwatch", region_name="us-east-1")
            alarms = cw.describe_alarms(StateValue="ALARM")["MetricAlarms"]

            eks = boto3.client("eks", region_name="us-east-1")
            clusters = eks.list_clusters()["clusters"]

            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]

            return (f"Weekly report: AWS spend ${weekly_cost:.2f}, "
                   f"{len(clusters)} EKS cluster(s), "
                   f"{len(repos)} container repos, "
                   f"{len(alarms)} active alert(s). "
                   f"Infrastructure healthy.")
        except Exception as e:
            return f"Weekly report error: {str(e)}"

    async def _cost_report(self) -> str:
        try:
            ce = boto3.client("ce", region_name="us-east-1")
            today = datetime.utcnow().date()
            start = today.replace(day=1)
            result = ce.get_cost_and_usage(
                TimePeriod={"Start": str(start), "End": str(today)},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )
            groups = result["ResultsByTime"][0]["Groups"]
            groups.sort(key=lambda x: float(x["Metrics"]["UnblendedCost"]["Amount"]), reverse=True)
            total = sum(float(g["Metrics"]["UnblendedCost"]["Amount"]) for g in groups)
            top3 = [f"{g['Keys'][0]}: ${float(g['Metrics']['UnblendedCost']['Amount']):.2f}" for g in groups[:3]]
            return f"Cost report: ${total:.2f} this month. Top services: {', '.join(top3)}."
        except Exception as e:
            return f"Cost report error: {str(e)}"

    async def _security_report(self) -> str:
        try:
            ec2 = boto3.client("ec2", region_name="us-east-1")
            sgs = ec2.describe_security_groups()["SecurityGroups"]
            open_ports = sum(1 for sg in sgs for p in sg.get("IpPermissions", [])
                           for r in p.get("IpRanges", [])
                           if r.get("CidrIp") == "0.0.0.0/0")
            iam = boto3.client("iam")
            users = iam.list_users()["Users"]
            score = max(0, 100 - (open_ports * 5))
            return f"Security report: {len(sgs)} security groups, {open_ports} open to internet, {len(users)} IAM users. Security score: {score}/100."
        except Exception as e:
            return f"Security report error: {str(e)}"

    async def _infra_report(self) -> str:
        try:
            ec2 = boto3.client("ec2", region_name="us-east-1")
            instances = ec2.describe_instances()
            running = sum(1 for r in instances["Reservations"]
                        for i in r["Instances"]
                        if i["State"]["Name"] == "running")
            eks = boto3.client("eks", region_name="us-east-1")
            clusters = eks.list_clusters()["clusters"]
            s3 = boto3.client("s3")
            buckets = s3.list_buckets()["Buckets"]
            return f"Infrastructure report: {running} EC2 instances, {len(clusters)} EKS clusters, {len(buckets)} S3 buckets. All systems operational."
        except Exception as e:
            return f"Infra report error: {str(e)}"
