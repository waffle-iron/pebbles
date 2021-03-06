CONFIG = {
    'schema': {
        'type': 'object',
        'title': 'Comment',
        'description': 'Description',
        'required': [
            'name',
            'image',
            'port',
            'openshift_cluster_id',
            'memory_limit',
        ],
        'properties': {
            'name': {
                'type': 'string'
            },
            'description': {
                'type': 'string'
            },
            'image': {
                'type': 'string',
            },
            'port': {
                'type': 'integer',
            },
            'volume_mount_point': {
                'type': 'string',
            },
            'openshift_cluster_id': {
                'type': 'string',
                'title': 'Cluster name (configured in credentials file)',
            },
            'memory_limit': {
                'type': 'string',
                'default': '512M',
            },
            'maximum_instances_per_user': {
                'type': 'integer',
                'title': 'Maximum instances per user',
                'default': 1,
            },
            'maximum_lifetime': {
                'type': 'string',
                'title': 'Maximum life-time (days hours mins)',
                'default': '1h 0m',
                'pattern': '^(\d+d\s?)?(\d{1,2}h\s?)?(\d{1,2}m\s?)?$',
                'validationMessage': 'Value should be in format [days]d [hours]h [minutes]m'
            },
            'environment_vars': {
                'type': 'string',
                'title': 'environment variables for docker, separated by space',
                'default': '',
            },
            'autodownload_url': {
                'type': 'string',
                'title': 'Autodownload URL',
                'default': '',
            },
            'autodownload_filename': {
                'type': 'string',
                'title': 'Autodownload file name',
                'default': '',
            },
        }
    },
    'form': [
        {
            'type': 'help',
            'helpvalue': '<h4>Docker instance config</h4>'
        },
        'name',
        'description',
        'image',
        'port',
        'volume_mount_point',
        'openshift_cluster_id',
        'environment_vars',
        'autodownload_url',
        'autodownload_filename',
        'memory_limit',
        'maximum_instances_per_user',
        'maximum_lifetime',
    ],
    'model': {
        'name': 'openshift_testing',
        'description': 'openshift testing template',
        'port': 8888,
        'image': '',
        'memory_limit': '512M',
    }
}
