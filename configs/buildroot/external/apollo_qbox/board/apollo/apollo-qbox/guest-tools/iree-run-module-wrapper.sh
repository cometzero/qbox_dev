#!/bin/sh
set -eu

real_runner=/usr/libexec/qbox/iree-run-module.real
apollo_runner=/usr/bin/apollo-iree-run-module
apollo_plugin=/usr/lib/qbox/libapollo_iree_hexagon_hal_plugin.so

is_apollo=0
has_query=0
has_plugin=0
prev=""

for arg in "$@"; do
  if [ "${prev}" = "--device" ]; then
    if [ "${arg}" = "apollo-hexagon" ] || [ "${arg}" = "apollo-hexagon://0" ]; then
      is_apollo=1
    fi
    prev=""
    continue
  fi

  case "${arg}" in
    --list_drivers|--dump_devices)
      has_query=1
      ;;
    --device=apollo-hexagon|--device=apollo-hexagon://0)
      is_apollo=1
      ;;
    --device)
      prev="--device"
      ;;
    --executable_plugin|--executable_plugin=*|--plugin|--plugin=*)
      has_plugin=1
      ;;
  esac
done

if [ "${is_apollo}" -eq 1 ] || [ "${has_query}" -eq 1 ]; then
  plugin_arg=""
  if [ "${has_plugin}" -eq 0 ] && [ -x "${apollo_plugin}" ]; then
    plugin_arg="--executable_plugin=${apollo_plugin}"
  fi
  exec "${apollo_runner}" ${plugin_arg:+"${plugin_arg}"} "$@"
fi

exec "${real_runner}" "$@"
