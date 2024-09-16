# This is the DAG (Directed acyclic graph) which is responsible for defining the workflow. Tbh it isnt all that bad but some things need to be changed...
# First we shouldnt need pod operators for everything, takes longer to spin up the pod than it does to download the protein, or copy over the database from Jupyter.
# this is also the OG one, i havent put the customized dag in here yet but ill change some minor detals such as the image.

from airflow import DAG, XComArg
from airflow.models.xcom_arg import MapXComArg
from airflow.models.param import Param
from airflow.decorators import dag, task, task_group
from airflow.configuration import conf
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator

from datetime import datetime

from kubernetes.client import models as k8s


# Specify the container image and Persistant volume class name
IMAGE_NAME = 'hwcopeland/autodock-all:latest' # Custom image from the ./docker/Dockerfile
PVC_NAME = 'pvc-autodock' # CHANGE ME

# Define the volume to dump data ?? what is Volume_key
MOUNT_PATH = '/data'
VOLUME_KEY  = 'volume-autodock'


## These params will be passed via api execution from Jupyter NB pods. Ive found 10000 ligand chunks works well
params = {
    # PDBID of the receptor, which will be used to fetch protein data from PDB
    'pdbid': '7cpa',

    # label of the ligand database, the filename for 
    # the corresponding database must be '{db_label}.sdf'
    'ligand_db': 'sweetlead',

    # number of ligands per chunk
    'ligands_chunk_size': 10000,
}

## What is this what is it calliing??
namespace = conf.get('kubernetes_executor', 'NAMESPACE')

@dag(start_date=datetime(2021, 1, 1),
     schedule=None,
     catchup=False,
     params=params)
def autodock(): 
    import os.path

    volume = k8s.V1Volume(
        name=VOLUME_KEY,
        persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(claim_name=PVC_NAME),
    )
    volume_mount = k8s.V1VolumeMount(mount_path=MOUNT_PATH, name=VOLUME_KEY)

    # define a generic container, which can be used for all tasks
    container = k8s.V1Container(
        name='autodock-container',
        image=IMAGE_NAME,
        working_dir=MOUNT_PATH,

        volume_mounts=[volume_mount],
        image_pull_policy='Always',
    )

    # CPU/generic pod specification
    pod_spec      = k8s.V1PodSpec(containers=[container], volumes=[volume])
    full_pod_spec = k8s.V1Pod(spec=pod_spec)

    # GPU-specific pod specification
    pod_spec_gpu      = k8s.V1PodSpec(containers=[container], volumes=[volume], runtime_class_name='nvidia')
    full_pod_spec_gpu = k8s.V1Pod(spec=pod_spec_gpu)

    # 1a - Prepare the protein
    prepare_receptor = KubernetesPodOperator(
        task_id='prepare_receptor',
        full_pod_spec=full_pod_spec,

        cmds=['/autodock/scripts/1a_fetch_prepare_protein.sh', '{{ params.pdbid }}'],
    )

    # split_sdf: <n> <db_label> ->  N_batches
    ## Can we randomize the database prior to splitting so that difficult to compute ligands get evenly distributed??
    split_sdf = KubernetesPodOperator(
        task_id='split_sdf',
        full_pod_spec=full_pod_spec,

        cmds = ['/bin/sh', '-c'],
        arguments=['/autodock/scripts/split_sdf.sh {{ params.ligands_chunk_size }} {{ params.ligand_db }} > /airflow/xcom/return.json'],
        do_xcom_push=True,
    )

    postprocessing = KubernetesPodOperator(
        task_id='postprocessing',
        full_pod_spec=full_pod_spec,

        cmds=['/autodock/scripts/3_post_processing.sh', '{{ params.pdbid }}', '{{ params.ligand_db }}'],
    )

    @task
    def get_batch_labels(db_label: str, n: int):
        return [f'{db_label}_batch{i}' for i in range(n+1)]

    @task_group
    def docking(batch_label: str):
        
        # prepare_ligands: <db_label> <batch_num> -> filelist_<db_label>_batch<batch_num>
        prepare_ligands = KubernetesPodOperator(
            task_id='prepare_ligands',
            full_pod_spec=full_pod_spec,
            get_logs=True,

            cmds=['/autodock/scripts/1b_prepare_ligands.sh'],
            arguments=['{{ params.pdbid }}', batch_label]
        )

        # perform_docking: <filelist> -> ()
        perform_docking = KubernetesPodOperator(
            task_id='perform_docking',
            full_pod_spec=full_pod_spec_gpu,
            container_resources=k8s.V1ResourceRequirements(
                limits={"nvidia.com/gpu": "1"}
            ),
            pool='gpu_pool',

            cmds=['/autodock/scripts/2_docking.sh'],
            arguments=['{{ params.pdbid }}', batch_label],
            get_logs=True
        )

        [prepare_receptor, prepare_ligands] >> perform_docking

    # converts (db_label, n) to a list of batch_labels
    batch_labels = get_batch_labels('sweetlead', split_sdf.output)

    # for each batch_label, we create a prepare_ligand + perform_docking task
    d = docking.expand(batch_label=batch_labels)
    
    # add post-processing
    d >> postprocessing

autodock()
