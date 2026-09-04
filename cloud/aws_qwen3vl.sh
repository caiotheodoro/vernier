#!/usr/bin/env bash
# Launches the Qwen3-VL judge on EC2, the deployment `cloud/modal_qwen3vl.py` named as the
# fallback ("AWS is the fallback once [Modal credits] run out ... a deployment change, not a
# code change on either side"). `src/vernier/judges/qwen3vl.py` reads `QWEN3VL_BASE_URL` and
# nothing else, so the judge code is untouched.
#
# Why this shape (each point checked live against the account, not assumed):
#
#   * g6.2xlarge, ON-DEMAND. The account's "Running On-Demand G and VT instances" quota is
#     8 vCPU, so g6.2xlarge (8 vCPU) fits exactly and g6.4xlarge (16) cannot launch at all.
#     GPU spot was 1.23 vs 1.32 USD/hr for g6.4xlarge when checked -- a ~7% discount for a real
#     interruption risk on a multi-hour judging run, which is not a trade worth making.
#   * L4, not A10G. vLLM's FP8 W8A8 needs compute capability >= 8.9. L4 is 8.9; the g5.xlarge
#     already stopped in this account is A10G at 8.6 and CANNOT run the pinned checkpoint.
#     `cloud/modal_qwen3vl.py` picked L4 for this exact reason.
#   * Frame extraction runs on the same box. It is ffmpeg range-reading HF's CDN, and
#     co-locating means the 20,000 extracted JPEGs are produced and consumed locally instead of
#     crossing the network twice. HF inbound to EC2 is free.
#   * vLLM binds to 127.0.0.1. The judge client runs on this same instance, so nothing needs to
#     be internet-facing -- strictly better than Modal's public endpoint, and it removes the
#     `--api-key` question entirely.
#
# Every pin below matches `cloud/modal_qwen3vl.py` exactly (model, revision, vLLM version,
# --max-model-len, --limit-mm-per-prompt). A different vLLM build silently makes these numbers
# non-comparable to the committed E2 runs, which is the whole reason D053 pinned sampling.
#
# Usage (from the laptop):
#   bash cloud/aws_qwen3vl.sh launch     # create the instance, wait for the server to answer
#   bash cloud/aws_qwen3vl.sh ssh        # shell in
#   bash cloud/aws_qwen3vl.sh terminate  # DELETE IT. An idle g6.2xlarge is ~$23/day.
set -euo pipefail

REGION="${REGION:-us-east-1}"
INSTANCE_TYPE="${INSTANCE_TYPE:-g6.2xlarge}"
KEY_NAME="${KEY_NAME:-plumb-diag2}"
VOLUME_GB="${VOLUME_GB:-150}"          # model ~9GB + 20k JPEGs ~4GB + image + headroom
TAG="vernier-h2-judge"

MODEL_NAME="Qwen/Qwen3-VL-8B-Instruct-FP8"
MODEL_REVISION="9cdc6310a8cb770ce18efaf4e9935334512aee45"
VLLM_VERSION="0.21.0"
VLLM_PORT=8000

# Ubuntu 22.04 base DL AMI: NVIDIA driver + docker preinstalled, so no CUDA install on boot.
# Resolved from AWS's own public SSM parameter rather than hardcoded -- a hardcoded AMI id goes
# stale silently and is region-specific.
ami_id() {
  aws ssm get-parameter --region "$REGION" \
    --name /aws/service/deeplearning/ami/x86_64/base-oss-nvidia-driver-gpu-ubuntu-22.04/latest/ami-id \
    --query 'Parameter.Value' --output text
}

instance_id() {
  aws ec2 describe-instances --region "$REGION" \
    --filters "Name=tag:Name,Values=$TAG" "Name=instance-state-name,Values=pending,running" \
    --query 'Reservations[].Instances[0].InstanceId' --output text
}

require_instance() {
  local id
  id="$(instance_id)"
  if [ -z "$id" ] || [ "$id" = "None" ]; then
    echo "no running instance tagged $TAG in $REGION -- launch one first" >&2
    exit 1
  fi
  echo "$id"
}

user_data() {
  cat <<EOF
#!/bin/bash
set -euxo pipefail
# vLLM's own published image: no pip resolution on the box, and the version is the pin.
docker run -d --restart unless-stopped --gpus all \\
  -p 127.0.0.1:${VLLM_PORT}:8000 \\
  -v /home/ubuntu/hf:/root/.cache/huggingface \\
  --ipc=host --name vllm \\
  vllm/vllm-openai:v${VLLM_VERSION} \\
    --model ${MODEL_NAME} \\
    --revision ${MODEL_REVISION} \\
    --served-model-name ${MODEL_NAME} \\
    --host 0.0.0.0 --port 8000 \\
    --tensor-parallel-size 1 \\
    --limit-mm-per-prompt '{"image": 1, "video": 0, "audio": 0}' \\
    --max-model-len 8192
EOF
}

case "${1:-}" in
  launch)
    AMI="$(ami_id)"; echo "AMI: $AMI"
    aws ec2 run-instances --region "$REGION" \
      --image-id "$AMI" --instance-type "$INSTANCE_TYPE" --key-name "$KEY_NAME" \
      --block-device-mappings "DeviceName=/dev/sda1,Ebs={VolumeSize=$VOLUME_GB,VolumeType=gp3,DeleteOnTermination=true}" \
      --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$TAG}]" \
      --user-data "$(user_data)" \
      --query 'Instances[0].InstanceId' --output text
    echo "launched. poll with: $0 status"
    ;;
  status)
    ID="$(require_instance)"; echo "instance: $ID"
    aws ec2 describe-instances --region "$REGION" --instance-ids "$ID" \
      --query 'Reservations[0].Instances[0].{state:State.Name,ip:PublicIpAddress}' --output json
    ;;
  ssh)
    IP=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$(require_instance)" \
          --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
    echo "ssh -L ${VLLM_PORT}:127.0.0.1:${VLLM_PORT} ubuntu@$IP"
    ;;
  terminate)
    ID="$(require_instance)"
    aws ec2 terminate-instances --region "$REGION" --instance-ids "$ID" \
      --query 'TerminatingInstances[0].{id:InstanceId,state:CurrentState.Name}' --output json
    ;;
  *)
    echo "usage: $0 {launch|status|ssh|terminate}" >&2; exit 2 ;;
esac
