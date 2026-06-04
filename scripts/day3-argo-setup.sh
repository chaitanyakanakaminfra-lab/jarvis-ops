#!/usr/bin/env bash
set -euo pipefail

ARGO_NAMESPACE="argo"
EVENTS_NAMESPACE="argo-events"
JARVIS_NAMESPACE="jarvis"

echo "=== STEP 1: Installing Argo Workflows ==="
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

helm upgrade --install argo-workflows argo/argo-workflows \
  --namespace "${ARGO_NAMESPACE}" --create-namespace \
  --version "0.41.14" \
  --set server.authMode=server \
  --set workflow.serviceAccount.create=true \
  --set workflow.serviceAccount.name=argo-workflow \
  --set controller.workflowNamespaces="{${ARGO_NAMESPACE},${JARVIS_NAMESPACE}}" \
  --wait
echo "Argo Workflows installed"

echo "=== STEP 2: RBAC for Jarvis namespace ==="
kubectl apply -f - <<EOF
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jarvis-workflow-sa
  namespace: ${JARVIS_NAMESPACE}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: jarvis-workflow-role
  namespace: ${JARVIS_NAMESPACE}
rules:
  - apiGroups: [""]
    resources: [pods, pods/log, configmaps, secrets]
    verbs: [get, list, watch, create, delete, patch]
  - apiGroups: [argoproj.io]
    resources: [workflows, workflowtemplates, cronworkflows]
    verbs: [get, list, watch, create, delete, patch, update]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: jarvis-workflow-rolebinding
  namespace: ${JARVIS_NAMESPACE}
subjects:
  - kind: ServiceAccount
    name: jarvis-workflow-sa
    namespace: ${JARVIS_NAMESPACE}
roleRef:
  kind: Role
  name: jarvis-workflow-role
  apiGroup: rbac.authorization.k8s.io
EOF

echo "=== STEP 3: Installing Argo Events ==="
helm upgrade --install argo-events argo/argo-events \
  --namespace "${EVENTS_NAMESPACE}" --create-namespace \
  --version "2.4.4" --wait

kubectl apply -n "${EVENTS_NAMESPACE}" \
  -f https://raw.githubusercontent.com/argoproj/argo-events/v1.9.2/examples/eventbus/native.yaml

echo "=== STEP 4: GitHub EventSource ==="
kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: EventSource
metadata:
  name: github-events
  namespace: ${EVENTS_NAMESPACE}
spec:
  github:
    jarvis-repo:
      repositories:
        - owner: chaitanyakanakaminfra-lab
          names: [jarvis-ops]
      webhook:
        endpoint: /github
        port: "12000"
        method: POST
      events: [pull_request, push]
      webhookSecret:
        name: github-webhook-secret
        key: secret
      insecure: false
      active: true
      contentType: json
EOF

echo "=== STEP 5: Schedule EventSource ==="
kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: EventSource
metadata:
  name: schedule-events
  namespace: ${EVENTS_NAMESPACE}
spec:
  calendar:
    weekly-cost-check:
      schedule: "0 8 * * 1"
      timezone: "UTC"
    nightly-security-scan:
      schedule: "0 23 * * *"
      timezone: "UTC"
    weekly-compliance:
      schedule: "0 6 * * 1"
      timezone: "UTC"
EOF

echo "=== Verification ==="
kubectl get pods -n "${ARGO_NAMESPACE}"
kubectl get pods -n "${EVENTS_NAMESPACE}"
echo ""
echo "Access Argo UI: kubectl -n argo port-forward svc/argo-workflows-server 2746:2746"
echo "=== Day 3 Complete ==="
