from airflow import DAG
from airflow.decorators import dag, task, task_group
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.configuration import conf
from kubernetes.client import models as k8s
from datetime import datetime, timedelta

IMAGE_NAME = 'hwcopeland/auto-docker:latest'
PVC_NAME = 'pvc-autodock'
MOUNT_PATH_AUTODOCK = '/data'
VOLUME_KEY_AUTODOCK = 'volume-autodock'

params = {
    'pdbid': '7jrn',
    'ligand_db': 'ChEBI_complete',
    'jupyter_user': 'jovyan',
    'native_ligand': 'TTT',
    'ligands_chunk_size': 10000,
}

namespace = conf.get('kubernetes_executor', 'NAMESPACE')

@dag(start_date=datetime(2021, 1, 1), schedule=None, catchup=False, params=params)
def autodock():
    volume_autodock = k8s.V1Volume(
        name=VOLUME_KEY_AUTODOCK,
        persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(claim_name=PVC_NAME),
    )
    volume_mount_autodock = k8s.V1VolumeMount(mount_path=MOUNT_PATH_AUTODOCK, name=VOLUME_KEY_AUTODOCK)

    jupyter_user_pvc = f"claim-{params['jupyter_user']}"
    VOLUME_KEY_USER = f"volume-user-{params['jupyter_user']}"
    MOUNT_PATH_USER = f"/home/{params['jupyter_user']}"

    volume_user = k8s.V1Volume(
        name=VOLUME_KEY_USER,
        persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(claim_name=jupyter_user_pvc),
    )
    volume_mount_user = k8s.V1VolumeMount(mount_path=MOUNT_PATH_USER, name=VOLUME_KEY_USER)

    container = k8s.V1Container(
        name='autodock-container',
        image=IMAGE_NAME,
        working_dir=MOUNT_PATH_AUTODOCK,
        volume_mounts=[volume_mount_autodock, volume_mount_user],
        image_pull_policy='Always',
    )

    pod_spec = k8s.V1PodSpec(containers=[container], volumes=[volume_autodock, volume_user])
    full_pod_spec = k8s.V1Pod(spec=pod_spec)

    copy_ligand_db = KubernetesPodOperator(
        task_id='copy_ligand_db',
        image='alpine',
        cmds=['/bin/sh', '-c'],
        arguments=[
            f'cp {MOUNT_PATH_USER}/{{{{ params.ligand_db }}}}.sdf {MOUNT_PATH_AUTODOCK}/{{{{ params.ligand_db }}}}.sdf'
        ],
        name='copy-ligand-db',
        volumes=[volume_autodock, volume_user],
        volume_mounts=[volume_mount_autodock, volume_mount_user],
        namespace=namespace,
        get_logs=True,
        retries=3,
        retry_delay=timedelta(minutes=5),
        is_delete_operator_pod=True,
    )

    prepare_receptor = KubernetesPodOperator(
        task_id='prepare_receptor',
        full_pod_spec=full_pod_spec,
        cmds=['python3','/autodock/scripts/proteinprepv2.py','--protein_id', '{{ params.pdbid }}','--ligand_id','{{ params.native_ligand }}'],
        retries=3,
        retry_delay=timedelta(minutes=5),
        is_delete_operator_pod=True,
    )

    split_sdf = KubernetesPodOperator(
        task_id='split_sdf',
        full_pod_spec=full_pod_spec,
        cmds=['/bin/sh', '-c'],
        arguments=['/autodock/scripts/split_sdf.sh {{ params.ligands_chunk_size }} {{ params.ligand_db }} > /airflow/xcom/return.json'],
        do_xcom_push=True,
        retries=3,
        retry_delay=timedelta(minutes=5),
        is_delete_operator_pod=True,
    )

    @task
    def get_batch_labels(batch_count: int, **context):
        ligand_db = context['params'].get('ligand_db')
        return [f"{ligand_db}_batch{i}" for i in range(batch_count + 1)] #maybe this will work?


    @task_group
    def docking(batch_label):
        prepare_ligands = KubernetesPodOperator(
            task_id='prepare_ligands',
            full_pod_spec=full_pod_spec,
            get_logs=True,
            cmds=['python3', '/autodock/scripts/ligandprepv2.py'],
            arguments=[
                '{{ ti.xcom_pull(task_ids="get_batch_labels")[ti.map_index] }}.sdf',
                f"{MOUNT_PATH_AUTODOCK}/output",
                '--format', 'pdb'
            ],
            env_vars={'MOUNT_PATH_AUTODOCK': MOUNT_PATH_AUTODOCK},
            is_delete_operator_pod=True,
        )

        perform_docking = KubernetesPodOperator(
            task_id='perform_docking',
            full_pod_spec=full_pod_spec,
            cmds=['python3','/autodock/scripts/dockingv2.sh'],
            arguments=['{{ params.pdbid }}', '{{ ti.xcom_pull(task_ids="get_batch_labels")[ti.map_index] }}'],
            get_logs=True,
            is_delete_operator_pod=True,
        )

        prepare_ligands >> perform_docking

    postprocessing = KubernetesPodOperator(
        task_id='postprocessing',
        full_pod_spec=full_pod_spec,
        cmds=['/autodock/scripts/3_post_processing.sh', '{{ params.pdbid }}', '{{ params.ligand_db }}'],
        retries=3,
        retry_delay=timedelta(minutes=5),
        is_delete_operator_pod=True,
    )

    copy_ligand_db >> prepare_receptor >> split_sdf

    batch_count = split_sdf.output
    batch_labels = get_batch_labels(batch_count)
    
    docking_tasks = docking.expand(batch_label=batch_labels)

    docking_tasks >> postprocessing

autodock()
