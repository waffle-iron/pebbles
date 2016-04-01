% Pouta Blueprints overview

# Overview

## Product 

- web interface to resources provisioned in the cloud
- open source project hosted at [GitHub](https://github.com/CSC-IT-Center-for-Science/pouta-blueprints)
- developed by CSC - IT Center for Science 
- buzzwords: Docker, Angular, RESTful, Ansible, self service, SAML2, notebook
- currently the resources can be VMs or containers

## Concepts

- system admins make _blueprints_, e.g. configurations
- users launch _instances_ of blueprints
- instances are time limited, quota limited, disposable
- users are authenticated (unlike http://tmpnb.org)
- user accounts are either
    - locally added by admin (via activation email)
    - based on SAML2 identity

## Service

- CSC runs a Pouta Blueprints server
- open to anyone with HAKA credentials
- currently in public beta
- blueprints for RStudio and IPython/Jupyter notebooks
- available at https://pb.csc.fi
- deployed in cPouta

