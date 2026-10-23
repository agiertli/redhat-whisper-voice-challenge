#!/usr/bin/env python3
"""Read-only RHDP preflight using captured oc JSON; standard library only."""
import json
import sys
from pathlib import Path


def check(directory, namespace, model, free_llama):
    def read(name):
        return json.loads((Path(directory) / (name + '.json')).read_text())

    operators = read('operators')['items']
    if not any(csv['metadata']['name'].startswith('rhods-operator.')
               and str(csv.get('spec', {}).get('version', '')).startswith('3.')
               and csv.get('status', {}).get('phase') == 'Succeeded'
               for csv in operators):
        raise ValueError('Expected a Succeeded OpenShift AI 3 operator CSV; inspect oc get csv -A. Other versions are unverified.')
    nodes = read('nodes')['items']
    candidates = {}
    for node in nodes:
        if node['metadata'].get('labels', {}).get('nvidia.com/gpu.present') != 'true':
            continue
        if node.get('spec', {}).get('unschedulable'):
            continue
        if not any(c['type'] == 'Ready' and c['status'] == 'True'
                   for c in node.get('status', {}).get('conditions', [])):
            continue
        capacity = int(node.get('status', {}).get('allocatable', {}).get('nvidia.com/gpu', '0'))
        if capacity:
            candidates[node['metadata']['name']] = capacity
    if not candidates:
        raise ValueError('No Ready, schedulable NVIDIA node with allocatable GPUs. Check GPU Operator/device plugin.')
    occupants = []
    for pod in read('pods')['items']:
        if pod.get('status', {}).get('phase') in ('Succeeded', 'Failed'):
            continue
        meta = pod['metadata']
        service = meta.get('labels', {}).get('serving.kserve.io/inferenceservice')
        if meta['namespace'] == namespace and service == model:
            continue  # Existing Whisper can reuse its GPU on upgrade.
        if free_llama and meta['namespace'] == 'my-first-model' and service == 'llama-32-3b-instruct':
            continue
        spec = pod['spec']
        normal = sum(int(c.get('resources', {}).get('limits', {}).get('nvidia.com/gpu', '0'))
                     for c in spec.get('containers', []))
        initial = max([int(c.get('resources', {}).get('limits', {}).get('nvidia.com/gpu', '0'))
                       for c in spec.get('initContainers', [])] or [0])
        requested = max(normal, initial)
        node = spec.get('nodeName')
        if requested and node in candidates:
            candidates[node] -= requested
            occupants.append(meta['namespace'] + '/' + meta['name'])
        elif requested and not node:
            raise ValueError('Another GPU pod is pending: ' + meta['namespace'] + '/' + meta['name'])
    if max(candidates.values()) < 1:
        raise ValueError('No GPU free for Whisper. Occupants: ' + ', '.join(occupants)
                         + '. On RHDP use --free-rhdp-gpu for the named demo Llama only.')
    storage = read('storage')['items']
    pvc = read('pvc')
    explicit_class = (Path(directory) / 'storage-class').read_text().strip()
    if not pvc.get('metadata'):
        if explicit_class:
            if not any(c['metadata']['name'] == explicit_class for c in storage):
                raise ValueError('Configured StorageClass does not exist: ' + explicit_class)
        elif not any(c['metadata'].get('annotations', {}).get('storageclass.kubernetes.io/is-default-class') == 'true'
                     or c['metadata'].get('annotations', {}).get('storageclass.beta.kubernetes.io/is-default-class') == 'true'
                     for c in storage):
            raise ValueError('No default StorageClass. Set tournament.storageClass in a values file.')
    print('GPU capacity and persistent storage checks passed (actual scheduling/pulls still require deployment).')


if __name__ == '__main__':
    try:
        check(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == 'true')
    except (ValueError, KeyError, OSError) as error:
        sys.exit('ERROR: ' + str(error))
