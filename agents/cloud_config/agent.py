import boto3
import structlog
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class CloudConfigAgent(BaseAgent):
    agent_id   = "cloud_config"
    agent_name = "Cloud Config Agent"

    async def _run(self, command: str) -> str:
        try:
            ec2 = boto3.client("ec2", region_name="us-east-1")
            
            # Check security groups for open ports
            sgs = ec2.describe_security_groups()["SecurityGroups"]
            open_sgs = []
            for sg in sgs:
                for rule in sg.get("IpPermissions", []):
                    for ip in rule.get("IpRanges", []):
                        if ip.get("CidrIp") == "0.0.0.0/0" and rule.get("FromPort") not in [80, 443, -1]:
                            open_sgs.append(sg["GroupName"])
                            break
            
            # Check VPCs
            vpcs = ec2.describe_vpcs()["Vpcs"]
            
            if open_sgs:
                return f"{len(vpcs)} VPC(s) configured. {len(open_sgs)} security group(s) have open inbound rules: {', '.join(open_sgs[:3])}. Review recommended."
            
            return f"{len(vpcs)} VPC(s) configured. {len(sgs)} security groups reviewed. No wide-open inbound rules detected. Cloud config looks clean."
        except Exception as e:
            logger.error("cloud_config.error", error=str(e))
            return f"Could not audit cloud config: {str(e)}"
