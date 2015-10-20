#!/bin/bash

# bail out on non-zero exit codes
set -e

DB_FILE=/webapps/pouta_blueprints/run/db.sqlite

print_usage() {
    echo "Usage: $0 -f export_file [-c]"
    echo "  -f <file> : export file to be loaded"
    echo "  -c        : clear out the old database"
}


# default export file name
export_date=$(/bin/date --iso-8601=seconds)
export_file=db.sqlite.$export_date.gz

while getopts "h?f:c" opt; do
    case "$opt" in
    h|\?)
        print_usage
        exit 0
        ;;
    f)  export_file=$OPTARG
        ;;
    c)  clean_database="1"
    esac
done

backup_file=$1

if [ ! -e $export_file ]; then
    echo "Backup file $backup_file not found"
    exit 1
fi

if [ "xxx$clean_database" != "xxx" ]; then
    current_date=$(/bin/date --iso-8601=seconds)

    echo "Stopping gunicorn http server workers"
    ssh www sudo supervisorctl stop gunicorn_app

    echo "Creating a copy of old database file"
    ssh www sudo cp $DB_FILE $DB_FILE.$current_date

    echo "Truncating database"
    ssh www sudo truncate --size 0 $DB_FILE

    echo "Loading export file $export_file into database"
    zcat $export_file | ssh www sudo sqlite3 $DB_FILE

    echo "Starting gunicorn http server workers"
    ssh www sudo supervisorctl start gunicorn_app
else
    echo "Loading  from $export_file"
    zcat $export_file | grep "^INSERT INTO" | ssh www sudo sqlite3 $DB_FILE
fi
