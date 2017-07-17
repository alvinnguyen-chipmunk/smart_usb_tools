#!/bin/sh
function retry {
  local n=1
  local max=$1
  local delay=$2
  local cmd="${@:3}"
  local retVal=0
  while true; do
	$cmd && break || {
	if [[ $n -lt $max ]]; then
	        ((n++))
		echo "Command failed. Attempt $n/$max:"
		for (( i = delay; i > 0; i-- )); do
			printf "Sleep: %02d\r" "${i}"
        		sleep 1
		done
	else
        	echo "The command has failed after $n attempts."
		retVal=1
		break
	fi
    }
  done

  return "$retVal"
}

#load default EMV configuration
cd /home/root/emv
retry 5 1 ./emv_load_config.sh
if [ "$?" -ne 0 ]; then
	echo "Failed to load default EMV configuration!!!Turn on CYAN LED"
	echo low > /sys/class/gpio/gpio150/direction
	echo high > /sys/class/gpio/gpio151/direction
	echo high > /sys/class/gpio/gpio152/direction	
	exit 1
fi
cd /home/root

