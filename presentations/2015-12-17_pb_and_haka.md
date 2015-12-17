% Pouta Blueprints and zero barrier of entry with HAKA
% Olli Tourunen @ SR Work Together 2015-12-17

# Overview

## Product 

- web interface to resources provisioned in the cloud
- open source project hosted at [GitHub](https://github.com/CSC-IT-Center-for-Science/pouta-blueprints)
- developed by DAC group
- buzzwords: Docker, Angular, RESTful, Ansible, self service, HAKA, notebook
- currently the resources can be VMs or containers

## Concepts

- system admins make _blueprints_, e.g. configurations
- users launch _instances_ of blueprints
- instances are time limited, quota limited, disposable
- users are authenticated (unlike http://tmpnb.org)
- user accounts are either
    - locally added by admin (via activation email)
    - based on HAKA identity

## Service

- CSC runs a Pouta Blueprints server
- open to anyone with HAKA credentials
- currently in public beta
- blueprints for RStudio and IPython/Jupyter notebooks
- available at https://pb.csc.fi
- deployed in cPouta

# Zero barrier me! [https://pb.csc.fi](https://pb.csc.fi)

# Use case: Notebooks for a course on pb.csc.fi

## The Professor 

"I would like to have an RStudio environment where I can just point my
students to by sharing a link. The environment should contain the latest
version of the exercises I made."
 
## The Professor 

- prepares a notebook for a lecture
- uploads it somewhere in the web
- points the students to https://pb.csc.fi

## The Students

- log in with HAKA
- launch an instance of the course blueprint
- learn something
- submit results 

## The System

- launches a new container per student
- downloads the newest version of the lecture notebook
- manages a pool of VMs running these containers
- removes VMs when they expire

##

(things are not exactly this simple, but more on that later)

# Private Deployment where barrier_of_entry > 0 

## Prerequisites

- a project in cPouta
- technical knowledge of 
    - running and customizing VMs in cloud
    - network and firewall setup

## Use case: VMs for students

## The Professor 

"I need each student to be able to launch one predefined VM for a limited amount of time. 
The students should not be able to manage resources in the cPouta project. It is tedious to
do this manually, although completely possible."

## The Professor

- obtains machine-to-machine credentials from cPouta support
- [installs and configures](https://github.com/CSC-IT-Center-for-Science/pouta-blueprints/blob/master/doc/how_to_install_on_cpouta.md) a Pouta Blueprints server in a VM in cPouta project
- configures the blueprint for the students
- sends an invitation mail to the students

## The Students

- register to the server via a link in the invitation mail
- upload their ssh key (PB can also generate one) 
- launch an instance of the blueprint
- log in to their VM via ssh

## The System

- sends the activation mails
- launches VMs in cPouta per request
- manages firewall(=security group rules) for the launched instances
- removes containers when they expire

# The Does Nots

## Permanent storage

- currently all instance data is deleted when the instance lifetime ends
- a permanent session concept would make the service useful for serious work
- many open questions from technical to policy level

## User grouping

- currently no grouping of users, just a flat list with admin flag on or off
- groups would be useful for 
    - limiting access and visibility to blueprints
    - creating global blacklists, whitelists

## Customer power users

- only admins can manage blueprints
- currently users that have admin rights are full admins
- in pb.csc.fi CSC admins will have to make all modifications to blueprints -> does not scale
- enter Customer power users
    - can create a user group
    - can assign selected properties of blueprints (whitelist, bootstrap url, ...)

## Accounting

- If pb.csc.fi takes off we need to introduce billing at some point
- especially so if we use it to host custom, private content for a closed course etc.


# The End

## Thanks

Talk to Aleksi, Apurva or Olli if you want to know more


