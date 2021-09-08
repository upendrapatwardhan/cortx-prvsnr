#!/bin/bash -x 

SCRIPT_DIR=$(dirname $0)

./$SCRIPT_DIR/destroy.sh

kubectl apply -f $SCRIPT_DIR/cortx-config-map.yml
kubectl apply -f $SCRIPT_DIR/cortx-config-pv.yml
kubectl apply -f $SCRIPT_DIR/cortx-config-pvc.yml
kubectl apply -f $SCRIPT_DIR/cortx-data-pod.yml

echo "Waiting for the containers to start up..."
sleep 5
kubectl get pods
kubectl describe pod cortx-data
kubectl logs cortx-data --container cortx-provisioner
