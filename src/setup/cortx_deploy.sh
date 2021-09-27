#!/bin/bash

function log_debug {
    [[ -z $DEBUG || $DEBUG != 1 ]] && return

    echo "log: $*"
}

function usage {
    echo "usage: $(basename $0) -n <node id> [-f <solution conf>]"
    echo "where:"
    echo "node id       - Unique Node ID"
    echo "solution conf - Solution conf dir containing cortx.yaml and cluster.yaml"
    echo
    exit 1
}

#[ $(id -u) -ne 0 ] && echo "error: run this command as root user" && exit 1

# Constants
SOLUTION_CONF="/etc/cortx/solution"
CORTX_CONF="/etc/cortx/cluster.yaml"

while [ $# -gt 0 ];  do
    case $1 in
    -d ) 
        DEBUG=1
        ;;

    -n ) 
        shift 1
        NODE_ID=$1
        ;;

    -f ) 
        shift 1
        SOLUTION_CONF=$1
        ;;
    
    esac
    shift 1
done

export PATH=$PATH:/opt/seagate/provisioner/bin

[ -z $NODE_ID ] && echo "error: missing node id parameter" && usage
echo $NODE_ID > "/etc/machine-id";
log_debug node_id=$NODE_ID
cortx_setup config apply -f $SOLUTION_CONF/cluster.yaml -o $CORTX_CONF;
cortx_setup config apply -f $SOLUTION_CONF/cortx.yaml -o $CORTX_CONF;
cortx_setup cluster bootstrap -f $CORTX_CONF;
