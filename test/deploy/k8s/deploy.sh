#!/bin/bash -x
SCRIPT_DIR=$(dirname $0)
"$SCRIPT_DIR"/destroy.sh
kubectl create namespace cortx
kubectl create cm solution-config --from-file="$SCRIPT_DIR"/cluster.yaml \
    --from-file="$SCRIPT_DIR"/config.yaml --namespace cortx

kubectl apply -f "$SCRIPT_DIR"/cortx-secret.yml --namespace cortx
kubectl apply -f "$SCRIPT_DIR"/cortx-pv-config.yml --namespace cortx
kubectl apply -f "$SCRIPT_DIR"/cortx-pvc-config.yml --namespace cortx
kubectl apply -f "$SCRIPT_DIR"/cortx-statefulset.yml --namespace cortx
echo "Waiting for the containers to start up..."
sleep 5

kubectl get statefulset podnode --namespace cortx
kubectl get pods --namespace cortx
pod=$(kubectl get pods --namespace cortx | grep podnode | awk '{print $1;}')
kubectl logs $pod --namespace cortx