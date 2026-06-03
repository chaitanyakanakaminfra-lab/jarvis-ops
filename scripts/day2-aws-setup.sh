#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="jarvis-cluster"
REGION="us-east-1"
NODE_TYPE="t3.medium"
NODE_MIN=1
NODE_MAX=3
NODE_DESIRED=2
K8S_VERSION="1.30"

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account: ${AWS_ACCOUNT_ID} | Region: ${REGION}"

echo "=== STEP 1: Creating EKS Cluster ==="
eksctl create cluster \
  --name "${CLUSTER_NAME}" \
  --region "${REGION}" \
  --version "${K8S_VERSION}" \
  --nodegroup-name "jarvis-nodes" \
  --node-type "${NODE_TYPE}" \
  --nodes "${NODE_DESIRED}" \
  --nodes-min "${NODE_MIN}" \
  --nodes-max "${NODE_MAX}" \
  --managed \
  --with-oidc \
  --ssh-access=false \
  --tags "Project=jarvis,ManagedBy=eksctl"

echo "=== STEP 2: Configuring kubectl ==="
aws eks update-kubeconfig --region "${REGION}" --name "${CLUSTER_NAME}"
kubectl get nodes

echo "=== STEP 3: Creating Namespaces ==="
kubectl create namespace jarvis      --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace argo        --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace argo-events --dry-run=client -o yaml | kubectl apply -f -

echo "=== STEP 4: Creating ECR Repositories ==="
REPOS=("jarvis/orchestrator" "jarvis/voice-server" "jarvis/agent-cicd" "jarvis/agent-infra" "jarvis/agent-cost" "jarvis/agent-security" "jarvis/agent-observability")
for REPO in "${REPOS[@]}"; do
  aws ecr create-repository --repository-name "${REPO}" --region "${REGION}" \
    --image-scanning-configuration scanOnPush=true \
    --tags Key=Project,Value=jarvis 2>/dev/null || echo "  (exists: ${REPO})"
  echo "  ok: ${REPO}"
done

echo "=== COST TIP ==="
echo "Scale down nodes when done:  eksctl scale nodegroup --cluster=${CLUSTER_NAME} --name=jarvis-nodes --nodes=0 --nodes-min=0 -r ${REGION}"
echo "Scale back up:               eksctl scale nodegroup --cluster=${CLUSTER_NAME} --name=jarvis-nodes --nodes=2 --nodes-min=1 -r ${REGION}"
echo "=== Day 2 Complete ==="
