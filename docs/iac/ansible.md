# Auto Dock Ansible


## Overview

Ansible is a built automation tool that will allow us to configure a kubernetes environment on multiple nodes as well as perform deployments against the kubernetes cluster. Ansible configurations should be versioned in github and include plain plain defaults to get someone up and running with the autodock project.


## Tasks

**General**
- [ ] Ansible:General: Create the outline of the ansible structure.
- [ ] Ansible:Automation: Create a docker image that will allow a user to run ansible commands without having to install ansible on their system.

**Kubernetes**
- [ ] Ansible:Kubernetes: Template each of the kubernetes services in the ias/ansible/templates/kubernetes directory
- [ ] Ansible:Kubernetes: Create an idempotent playbook outline to bootstrap the kubernetes cluster.

**airflow**
- [ ] Ansible:Airflow: Create a playbook to update the ligands.
- [ ] Ansible:Airflow: Create a playbook to bootstrap airflow.


## Ansible
```plantuml
@startuml
!theme blueprint
left to right direction
title Structure
node "ansible docker"

component "workspace" {
  component Ansible {
    top to bottom direction
    ["Kubernetes"]
    ["Autodock"]
  }
  component Configs {

  }
  component Repo {

  }
}
"ansible docker" -d-> "Ansible"

component "cluster" {
  top to bottom direction
  node k8s1
  node k8s2
  node k8s3
}

@enduml
```

- Docker will run ansible and perform the running of the runbooks.
- Kubernetes deploy playbook will:
  - Install and update host OS and required packages
  - Copy the templated files from the configs directory.
  - Use Kubeadm/Kubectl to setup the pods.
  - Startup pod services.

- Autodock playbook will:
  - Deploy the repo code changes to the given pod.

- This can be extended to support runbooks which we can leverage to grab error logs/reports on the system and it's operations until a better form of metrics/logging can be arranged.