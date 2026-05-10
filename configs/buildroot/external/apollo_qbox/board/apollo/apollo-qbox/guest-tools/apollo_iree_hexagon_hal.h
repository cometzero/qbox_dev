/* SPDX-License-Identifier: MIT */
#ifndef APOLLO_IREE_HEXAGON_HAL_H
#define APOLLO_IREE_HEXAGON_HAL_H

#include <stddef.h>
#include <stdint.h>

#include "apollo_hexagon_uapi_guest.h"

#define APOLLO_HEXAGON_HAL_STATUS_OK 0x434e4e4f
#define APOLLO_HEXAGON_HAL_STATUS_SG_OK 0x53474f4b

struct apollo_hexagon_executable {
	char module_path[256];
	char plugin_path[256];
	char entry_point[96];
	char expected_output[160];
	size_t module_size;
};

struct apollo_hexagon_command_buffer {
	uint32_t input[APOLLO_HEXAGON_CNN_INPUT_WORDS];
	uint32_t output[APOLLO_HEXAGON_CNN_OUTPUT_WORDS];
	uint32_t status;
};

struct apollo_hexagon_fence {
	uint32_t signaled;
	uint32_t status;
	uint32_t queue_id;
	uint32_t fence_seq;
};

struct apollo_hexagon_queue {
	int fd;
	const char *device;
	uint32_t queue_id;
	uint32_t queue_count;
};

int apollo_hexagon_load_executable(const char *metadata_path,
					   const char *module_override,
					   struct apollo_hexagon_executable *exe,
					   char *error, size_t error_len);
int apollo_hexagon_queue_open(struct apollo_hexagon_queue *queue,
				      const char *device, char *error, size_t error_len);
void apollo_hexagon_queue_close(struct apollo_hexagon_queue *queue);
void apollo_hexagon_queue_select(struct apollo_hexagon_queue *queue,
				 uint32_t queue_id);
int apollo_hexagon_queue_submit_cnn(struct apollo_hexagon_queue *queue,
				    struct apollo_hexagon_command_buffer *cmd,
				    struct apollo_hexagon_fence *fence,
				    char *error, size_t error_len);
int apollo_hexagon_queue_submit_dma_stress(struct apollo_hexagon_queue *queue,
					   uint32_t bytes, uint32_t seed,
					   uint32_t *checksum,
					   struct apollo_hexagon_fence *fence,
					   char *error, size_t error_len);

#endif /* APOLLO_IREE_HEXAGON_HAL_H */
