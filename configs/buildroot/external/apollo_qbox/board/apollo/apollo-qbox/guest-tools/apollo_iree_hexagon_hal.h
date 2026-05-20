/* SPDX-License-Identifier: MIT */
#ifndef APOLLO_IREE_HEXAGON_HAL_H
#define APOLLO_IREE_HEXAGON_HAL_H

#include <stddef.h>
#include <stdint.h>

#include "apollo_hexagon_uapi_guest.h"

#define APOLLO_HEXAGON_HAL_STATUS_OK 0x434e4e4f
#define APOLLO_HEXAGON_HAL_STATUS_VADD_OK 0x56414444
#define APOLLO_HEXAGON_HAL_STATUS_SG_OK 0x53474f4b

struct apollo_hexagon_executable {
	char module_path[256];
	char plugin_path[256];
	char compiler_name[64];
	char compiler_artifact_path[256];
	char apko_path[256];
	char entry_point[96];
	char expected_output[160];
	const void *apko_data;
	size_t module_size;
	size_t compiler_artifact_size;
	size_t apko_size;
	size_t apko_data_size;
	uint32_t executable_format;
	uint32_t apko_abi_version;
	uint32_t entry_kind;
	uint32_t input_bytes;
	uint32_t output_bytes;
	uint32_t apko_embedded;
};

struct apollo_hexagon_command_buffer {
	uint32_t input[APOLLO_HEXAGON_CNN_INPUT_WORDS];
	uint32_t output[APOLLO_HEXAGON_CNN_OUTPUT_WORDS];
	uint32_t status;
};

struct apollo_hexagon_vadd_command_buffer {
	uint32_t lhs[APOLLO_HEXAGON_VADD_WORDS];
	uint32_t rhs[APOLLO_HEXAGON_VADD_WORDS];
	uint32_t output[APOLLO_HEXAGON_VADD_OUTPUT_WORDS];
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
	char device_path[64];
	const char *device;
	uint32_t queue_id;
	uint32_t queue_count;
	uint32_t generic_abi_version;
	uint32_t supported_executable_formats;
	uint32_t max_command_bytes;
	uint32_t max_bindings_per_dispatch;
	uint32_t max_queue_depth;
	uint32_t fence_model;
	uint32_t smmu_page_granularity;
	uint32_t fault_record_size;
};

int apollo_hexagon_load_executable(const char *metadata_path,
					   const char *module_override,
					   struct apollo_hexagon_executable *exe,
					   char *error, size_t error_len);
void apollo_hexagon_unload_executable(struct apollo_hexagon_executable *exe);
int apollo_hexagon_queue_open(struct apollo_hexagon_queue *queue,
				      const char *device, char *error, size_t error_len);
void apollo_hexagon_queue_close(struct apollo_hexagon_queue *queue);
void apollo_hexagon_queue_select(struct apollo_hexagon_queue *queue,
				 uint32_t queue_id);
int apollo_hexagon_queue_submit_cnn(struct apollo_hexagon_queue *queue,
				    struct apollo_hexagon_command_buffer *cmd,
				    struct apollo_hexagon_fence *fence,
				    char *error, size_t error_len);
int apollo_hexagon_queue_submit_vadd(struct apollo_hexagon_queue *queue,
				     struct apollo_hexagon_vadd_command_buffer *cmd,
				     struct apollo_hexagon_fence *fence,
				     char *error, size_t error_len);
int apollo_hexagon_queue_submit_apko(
	struct apollo_hexagon_queue *queue,
	const struct apollo_hexagon_executable *exe, const void *input,
	size_t input_bytes, void *output, size_t output_bytes,
	struct apollo_hexagon_fence *fence, char *error, size_t error_len);
int apollo_hexagon_queue_submit_dma_stress(struct apollo_hexagon_queue *queue,
					   uint32_t bytes, uint32_t seed,
					   uint32_t *checksum,
					   struct apollo_hexagon_fence *fence,
					   char *error, size_t error_len);

#endif /* APOLLO_IREE_HEXAGON_HAL_H */
