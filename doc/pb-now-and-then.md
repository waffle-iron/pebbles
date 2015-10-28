% Pouta Blueprints now and then
% Olli Tourunen @ DAC Team Afternoon
% 2015-10-28


# Overview

- Web interface to resources provisioned in the cloud
- System admins make blueprints, e.g. configurations
- Users launch instances of blueprints
- Instances are time limited
- Users are authenticated
- Accounts 
    - can be added by admin
    - can come from HAKA 

## Under the hood

- Angular/restangular/bootstrap for WEB UI
- flask/restful/sqlite/sqlalchemy for REST API
- backend = www + worker (+proxy)
- celery + redis for communication between components
- Driver plugins for different kinds of provisioned resources
- blueprint = driver + configuration

# PoutaBlueprints now

## Deployment
- using ansible to install and configure software
- devel installation: vagrant + ansible
    - can run in docker or virtualbox 
- server installation: docker + ansible
    - separate containers for www, worker, proxy
    - containers created by ansible
    - single server hosts all containers

## OpenStackDriver

- user interface: ssh to a public IP
- single VM instances
- initialization scripts (cloud init)
- custom firewall policy
- customer can open ssh access from a single IP
- simple, working

## PvcCmdLineDriver

- user interface: ssh to a public IP
- wrapper around pouta-virtualcluster
- clusters of VMs
- custom firewall policy
- customer can open ssh access from a single IP
- command-line based invocation of PVC
- complex, working

## DockerDriver

- launch containers on a pool of hosts
- host pool is scaled up (and down) as needed
- single container port is exposed through a proxy
- good for hosting disposable notebooks
- RStudio and Jupyter images working

# PoutaBlueprints then

## OpenStackDriver

- No big hurts, no big plans

## PvcCmdLineDriver

- this was the first driver implementation, and the first to go
- should be replaced with something more tightly integrated
    - make use of OpenStackService
    - control state and resources within the PB infrastructure
    - strip the number of supported applications down to Spark+Hadoop2

## DockerDriver

- image transfer/population pain points
    - currently the docker images are pushed once during host preparation
    - images need to be pulled by the admin from the command line to server in advance
    - when the number of images grows, it becomes impossible to have them all preloaded to
      all of the pool hosts
      
- custom images for e.g. a course with special needs should be made easier 
    - currently have to be rolled in advance by the admin
    - no dynamic content support

- it should be possible to expose common/example datasets as read-only 
    
- currently user data is not persistent
    - it would be very useful to be able to just continue working where you left 
      without manual import/export
    - tricky to do right

# Ideas for improvement

## System deployment overhaul

- from fat containers to proper per-process containers
- keep state out of containers
- container-optimized hosts? (CoreOS? Project Atomic?)
- fully automated VM orchestration (Terraform? Heat? Ansible?)


## New features 

- possibility to operate on groups of people

- access control for blueprints per group

- also see github issues page at https://github.com/CSC-IT-Center-for-Science/pouta-blueprints/issues

