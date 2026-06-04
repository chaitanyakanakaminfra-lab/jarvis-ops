"""
agents/cicd/voice_responses.py
────────────────────────────────
All spoken responses for the CI/CD Pipeline agent.

Interview explanation:
  "I keep voice responses separate from agent logic so they're easy
   to tune without touching the core code. Each function returns a
   natural sentence Jarvis speaks back — short, direct, factual."
"""


def pipeline_started(pr_number: int | None = None, workflow_name: str = "") -> str:
    if pr_number:
        return f"Pipeline started for PR {pr_number}. Workflow {workflow_name} is running."
    return f"Pipeline started. Workflow {workflow_name} is now running on EKS."


def pipeline_succeeded(workflow_name: str, duration_s: int = 0) -> str:
    if duration_s:
        return f"Pipeline succeeded. {workflow_name} completed in {duration_s} seconds."
    return f"Pipeline succeeded. {workflow_name} completed successfully."


def pipeline_failed(workflow_name: str, reason: str = "") -> str:
    if reason:
        return f"Pipeline failed. {workflow_name} encountered an error: {reason}."
    return f"Pipeline failed. Check the Argo UI for {workflow_name} logs."


def deploy_started(environment: str = "production") -> str:
    return f"Deployment to {environment} has started. I will notify you when it completes."


def deploy_succeeded(environment: str = "production", version: str = "") -> str:
    if version:
        return f"Version {version} deployed successfully to {environment}."
    return f"Deployment to {environment} completed successfully."


def deploy_failed(environment: str = "production", reason: str = "") -> str:
    return f"Deployment to {environment} failed. {reason}. Rolling back now."


def no_pipeline_found(template_name: str) -> str:
    return f"I could not find a workflow template named {template_name}. Please check the Argo UI."


def pipeline_status(workflow_name: str, phase: str) -> str:
    phase_map = {
        "Running": "is currently running",
        "Succeeded": "completed successfully",
        "Failed": "has failed",
        "Pending": "is pending",
        "Error": "encountered an error",
    }
    status = phase_map.get(phase, f"is in {phase} state")
    return f"Workflow {workflow_name} {status}."
