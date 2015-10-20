#!/bin/bash

# bail out on non-zero exit codes
set -e

DB_FILE=/webapps/pouta_blueprints/run/db.sqlite

print_usage() {
    echo "Usage: $0 [-f export_file] [-t table_pattern]"
}

# default export file name
export_date=$(/bin/date --iso-8601=seconds)
export_file="db.sqlite.$export_date.gz"

table_pattern=""

while getopts "h?t:f:" opt; do
    case "$opt" in
    h|\?)
        print_usage
        exit 0
        ;;
    t)  table_pattern=$OPTARG
        ;;
    f)  export_file=$OPTARG
        ;;
    esac
done

shift $((OPTIND-1))

if [ -e $export_file ]; then
    echo "Export file $export_file already exists, remove it first"
    exit 1
fi

echo "Exporting to $export_file"
if [ "xxx$table_pattern" != "xxx" ]; then
    echo "match tables with pattern '$table_pattern'"
fi

ssh www "echo '.dump $table_pattern' | sudo sqlite3 $DB_FILE" | gzip -c > $export_file
