DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
for file in $DIR/*
do
	if [ ${file: -5} == ".json" ]
	then
		echo "==> $file"  
		$DIR/emv_upgrade_config_json "$file"
		retVal="$?"
		if [ $retVal -ne 0 ]; then
			echo "Faied with error code: $retVal"
			exit 1
		fi
	fi
done
exit 0

