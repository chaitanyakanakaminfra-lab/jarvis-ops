#!/usr/bin/env bash
set -euo pipefail

REGION="us-east-1"
JARVIS_NAMESPACE="jarvis"
CLUSTER_NAME="jarvis-cluster"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "=== STEP 1: AWS Secrets Manager ==="
store_secret() {
  local NAME=$1 VALUE=$2
  aws secretsmanager create-secret --name "${NAME}" --secret-string "${VALUE}" \
    --region "${REGION}" --tags Key=Project,Value=jarvis 2>/dev/null || \
  aws secretsmanager put-secret-value --secret-id "${NAME}" \
    --secret-string "${VALUE}" --region "${REGION}"
  echo "  stored: ${NAME}"
}

store_secret "jarvis/openai"      '{"api_key": "'"${OPENAI_API_KEY:-REPLACE_ME}"'"}'
store_secret "jarvis/elevenlabs"  '{"api_key": "'"${ELEVENLABS_API_KEY:-REPLACE_ME}"'", "voice_id": "'"${ELEVENLABS_VOICE_ID:-REPLACE_ME}"'"}'
store_secret "jarvis/deepgram"    '{"api_key": "'"${DEEPGRAM_API_KEY:-REPLACE_ME}"'"}'
store_secret "jarvis/porcupine"   '{"access_key": "'"${PORCUPINE_ACCESS_KEY:-REPLACE_ME}"'"}'
store_secret "jarvis/github"      '{"token": "'"${GITHUB_TOKEN:-REPLACE_ME}"'", "webhook_secret": "'"${GITHUB_WEBHOOK_SECRET:-REPLACE_ME}"'"}'
store_secret "jarvis/postgres"    '{"host": "postgres", "port": "5432", "db": "jarvis", "user": "jarvis", "password": "'"${POSTGRES_PASSWORD:-changeme}"'"}'

echo "=== STEP 2: External Secrets Operator ==="
helm repo add external-secrets https://charts.external-secrets.io
helm repo update
helm upgrade --install external-secrets external-secrets/external-secrets \
  --namespace external-secrets --create-namespace --set installCRDs=true --wait

echo "=== STEP 3: IAM Role for ESO (IRSA) ==="
OIDC_PROVIDER=$(aws eks describe-cluster --name "${CLUSTER_NAME}" \
  --region "${REGION}" --query "cluster.identity.oidc.issuer" \
  --output text | sed 's|https://||')

cat > /tmp/eso-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["secretsmanager:GetSecretValue","secretsmanager:DescribeSecret","secretsmanager:ListSecretVersionIds"],
    "Resource": "arn:aws:secretsmanager:${REGION}:${AWS_ACCOUNT_ID}:secret:jarvis/*"
  }]
}
EOF

aws iam create-policy --policy-name JarvisESOPolicy \
  --policy-document file:///tmp/eso-policy.json 2>/dev/null || echo "  (policy exists)"

cat > /tmp/eso-trust.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/${OIDC_PROVIDER}"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "${OIDC_PROVIDER}:sub": "system:serviceaccount:external-secrets:external-secrets",
        "${OIDC_PROVIDER}:aud": "sts.amazonaws.com"
      }
    }
  }]
}
EOF

aws iam create-role --role-name JarvisESORole \
  --assume-role-policy-document file:///tmp/eso-trust.json 2>/dev/null || echo "  (role exists)"
aws iam attach-role-policy --role-name JarvisESORole \
  --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/JarvisESOPolicy"

echo "=== STEP 4: SecretStore + ExternalSecrets ==="
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secrets-manager
spec:
  provider:
    aws:
      service: SecretsManager
      region: ${REGION}
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets
            namespace: external-secrets
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: openai-secret
  namespace: ${JARVIS_NAMESPACE}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: openai-secret
    creationPolicy: Owner
  data:
    - secretKey: api_key
      remoteRef:
        key: jarvis/openai
        property: api_key
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: voice-secrets
  namespace: ${JARVIS_NAMESPACE}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: voice-secrets
    creationPolicy: Owner
  data:
    - secretKey: elevenlabs_api_key
      remoteRef:
        key: jarvis/elevenlabs
        property: api_key
    - secretKey: deepgram_api_key
      remoteRef:
        key: jarvis/deepgram
        property: api_key
    - secretKey: porcupine_access_key
      remoteRef:
        key: jarvis/porcupine
        property: access_key
EOF

echo "=== STEP 5: Terraform State (S3 + DynamoDB) ==="
STATE_BUCKET="jarvis-terraform-state-${AWS_ACCOUNT_ID}"
LOCK_TABLE="jarvis-terraform-locks"

aws s3api create-bucket --bucket "${STATE_BUCKET}" --region "${REGION}" 2>/dev/null || echo "  (bucket exists)"
aws s3api put-bucket-versioning --bucket "${STATE_BUCKET}" \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "${STATE_BUCKET}" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket "${STATE_BUCKET}" \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

aws dynamodb create-table --table-name "${LOCK_TABLE}" \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST --region "${REGION}" \
  --tags Key=Project,Value=jarvis 2>/dev/null || echo "  (table exists)"

echo "  S3 bucket: ${STATE_BUCKET}"
echo "  DynamoDB:  ${LOCK_TABLE}"
echo "=== Day 4 Complete ==="
