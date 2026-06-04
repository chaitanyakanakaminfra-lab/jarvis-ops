"""
agents/docker_image/voice_responses.py
────────────────────────────────────────
Spoken responses for the Docker & Image agent.
"""


def build_started(image_name: str = "") -> str:
    if image_name:
        return f"Building Docker image {image_name} now."
    return "Docker build started. I will notify you when it completes."


def build_succeeded(image_name: str, tag: str = "latest") -> str:
    return f"Docker image {image_name}:{tag} built successfully."


def build_failed(image_name: str, reason: str = "") -> str:
    if reason:
        return f"Docker build failed for {image_name}. {reason}."
    return f"Docker build failed for {image_name}. Check the build logs."


def push_started(registry: str = "ECR") -> str:
    return f"Pushing image to {registry} now."


def push_succeeded(image_name: str, registry: str = "ECR") -> str:
    return f"Image {image_name} pushed to {registry} successfully."


def push_failed(image_name: str, reason: str = "") -> str:
    if reason:
        return f"Failed to push {image_name}. {reason}."
    return f"Failed to push {image_name} to the registry."


def mirror_started(source: str, target: str) -> str:
    return f"Mirroring image from {source} to {target}."


def mirror_succeeded(image_name: str) -> str:
    return f"Image {image_name} mirrored to ECR successfully."


def mirror_failed(image_name: str, reason: str = "") -> str:
    return f"Failed to mirror {image_name}. {reason}."


def scan_started(image_name: str) -> str:
    return f"Scanning {image_name} for vulnerabilities using Trivy."


def scan_clean(image_name: str) -> str:
    return f"No vulnerabilities found in {image_name}. Image is clean."


def scan_found(image_name: str, critical: int, high: int) -> str:
    if critical > 0:
        return f"Critical alert — {image_name} has {critical} critical and {high} high CVEs. Deploy blocked."
    return f"{image_name} has {high} high severity CVEs. Review before deploying."


def no_image_specified() -> str:
    return "Please specify an image name. For example: build the orchestrator image."
