import os
import sys
import yaml


def extract_packages(yaml_data):
    if not yaml_data:
        return []

    res = []
    for task in yaml_data:
        if 'apt' in task:
            pkg_type = 'apt'
        elif 'yum' in task:
            pkg_type = 'yum'
        else:
            continue
        if 'with_items' in task:
            for package in task['with_items']:
                res.append('%s: %s' % (pkg_type, package))
        else:
            params = task[pkg_type].split()
            task_dict = {}
            for param in params:
                key, value = param.split('=')
                task_dict[key] = value

            if 'state' in task_dict and task_dict['state'] == 'absent':
                continue

            for key in task_dict:
                if key == 'pkg' or key == 'name':
                    res.append('%s: %s' % (pkg_type, task_dict[key]))

    return res


def main():
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    else:
        root_dir = '.'

    print "Using root directory %s" % root_dir

    for cur_dir, dirs, files in os.walk(root_dir):
        for f in files:
            if f.endswith('yml'):
                with open('%s/%s' % (cur_dir, f), 'r') as yaml_file:
                    packages = extract_packages(yaml.load(yaml_file))
                if len(packages) > 0:
                    print '%s/%s' % (cur_dir, f)
                    for p in packages:
                        print p
                    print


if __name__ == '__main__':
    main()