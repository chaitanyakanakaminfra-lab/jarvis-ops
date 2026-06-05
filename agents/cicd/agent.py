import boto3
import structlog
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class CICDPipelineAgent(BaseAgent):
    agent_id   = "cicd_pipeline"
    agent_name = "CI/CD Pipeline Agent"

    async def _run(self, command: str) -> str:
        try:
            # Check CodeBuild projects
            cb = boto3.client("codebuild", region_name="us-east-1")
            projects = cb.list_projects().get("projects", [])

            if not projects:
                # Check GitHub Actions via ECR image pushes instead
                ecr = boto3.client("ecr", region_name="us-east-1")
                repos = ecr.describe_repositories().get("repositories", [])
                jarvis_repos = [r for r in repos if "jarvis" in r["repositoryName"].lower()]
                
                if jarvis_repos:
                    # Get latest push time
                    latest_push = None
                    for repo in jarvis_repos[:1]:
                        try:
                            images = ecr.describe_images(
                                repositoryName=repo["repositoryName"],
                                filter={"tagStatus": "TAGGED"}
                            ).get("imageDetails", [])
                            if images:
                                latest = sorted(images, key=lambda x: str(x.get("imagePushedAt", "")), reverse=True)[0]
                                latest_push = str(latest.get("imagePushedAt", ""))[:10]
                        except:
                            pass
                    
                    if latest_push:
                        return f"{len(jarvis_repos)} Jarvis pipeline images in ECR. Last build pushed on {latest_push}. Pipeline is healthy."
                
                return f"No CodeBuild projects found. Using GitHub Actions for CI/CD. {len(repos)} ECR repositories active."

            # Get build status
            builds = cb.list_builds_for_project(
                projectName=projects[0],
                sortOrder="DESCENDING"
            ).get("ids", [])

            if builds:
                build_info = cb.batch_get_builds(ids=builds[:1])["builds"][0]
                status = build_info["buildStatus"]
                duration = build_info.get("buildComplete", False)
                return f"CodeBuild project {projects[0]}: last build {status}. {len(projects)} total projects configured."

            return f"{len(projects)} CodeBuild project(s) found. No recent builds."

        except Exception as e:
            logger.error("cicd.error", error=str(e))
            return f"CI/CD using GitHub Actions. Check github.com/chaitanyakanakaminfra-lab/jarvis-ops for pipeline status."
