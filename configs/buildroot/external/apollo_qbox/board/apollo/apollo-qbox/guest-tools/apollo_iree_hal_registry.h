/* SPDX-License-Identifier: MIT */
#ifndef APOLLO_IREE_HAL_REGISTRY_H
#define APOLLO_IREE_HAL_REGISTRY_H

#include <stddef.h>

#include "apollo_iree_hexagon_hal.h"
#include "apollo_iree_hexagon_plugin.h"

struct apollo_iree_hal_device {
	const char *name;
	const char *description;
	const char *plugin_path;
	const struct apollo_iree_hexagon_plugin_v1 *ops;
};

const struct apollo_iree_hal_device *apollo_iree_hal_registry_lookup(
	const char *device_name, const char *plugin_path, char *error,
	size_t error_len);

void apollo_iree_hal_registry_unload_plugin(void);

int apollo_iree_hal_registry_open_queue(
	const struct apollo_iree_hal_device *device,
	struct apollo_hexagon_queue *queue, const char *device_path,
	char *error, size_t error_len);

#endif /* APOLLO_IREE_HAL_REGISTRY_H */
