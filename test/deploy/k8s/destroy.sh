#!/bin/bash -x

kubectl delete -f ./cortx-statefulset.yml --namespace cortx
kubectl delete pvc cortx-config-pvc --namespace cortx
kubectl delete pv cortx-config-pv --namespace cortx
kubectl delete cm solution-config --namespace cortx
kubectl delete secret cortx-secret --namespace cortx
kubectl delete namespace cortx