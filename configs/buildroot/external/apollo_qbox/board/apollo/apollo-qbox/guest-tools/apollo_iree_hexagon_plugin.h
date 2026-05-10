/* SPDX-License-Identifier: MIT */
#ifndef APOLLO_IREE_HEXAGON_PLUGIN_H
#define APOLLO_IREE_HEXAGON_PLUGIN_H

#include <stddef.h>
#include <stdint.h>

#include "apollo_iree_hexagon_hal.h"

#define APOLLO_IREE_HEXAGON_PLUGIN_API_VERSION 1u
#define APOLLO_IREE_HEXAGON_PLUGIN_EXPORT_NAME "apollo_iree_hexagon_plugin_query"

struct apollo_iree_hexagon_plugin_v1 {
	uint32_t api_version;
	const char *name;
	const char *description;
	int (*queue_open)(struct apollo_hexagon_queue *queue, const char *device,
			  char *error, size_t error_len);
	void (*queue_close)(struct apollo_hexagon_queue *queue);
	void (*queue_select)(struct apollo_hexagon_queue *queue,
			     uint32_t queue_id);
	int (*queue_submit_cnn)(struct apollo_hexagon_queue *queue,
				struct apollo_hexagon_command_buffer *cmd,
				struct apollo_hexagon_fence *fence,
				char *error, size_t error_len);
	int (*queue_submit_dma_stress)(struct apollo_hexagon_queue *queue,
				       uint32_t bytes, uint32_t seed,
				       uint32_t *checksum,
				       struct apollo_hexagon_fence *fence,
				       char *error, size_t error_len);
};

typedef const struct apollo_iree_hexagon_plugin_v1 *(
	*apollo_iree_hexagon_plugin_query_fn_t)(uint32_t max_version);

#endif /* APOLLO_IREE_HEXAGON_PLUGIN_H */
