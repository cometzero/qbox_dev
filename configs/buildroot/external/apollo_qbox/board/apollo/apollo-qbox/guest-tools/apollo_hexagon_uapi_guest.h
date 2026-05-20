/* SPDX-License-Identifier: MIT */
#ifndef APOLLO_HEXAGON_UAPI_GUEST_H
#define APOLLO_HEXAGON_UAPI_GUEST_H

#include <stdint.h>
#include <sys/ioctl.h>

#define APOLLO_HEXAGON_CNN_INPUT_WORDS 16
#define APOLLO_HEXAGON_CNN_OUTPUT_WORDS 4
#define APOLLO_HEXAGON_VADD_WORDS 4
#define APOLLO_HEXAGON_VADD_INPUT_WORDS (APOLLO_HEXAGON_VADD_WORDS * 2)
#define APOLLO_HEXAGON_VADD_OUTPUT_WORDS APOLLO_HEXAGON_VADD_WORDS
#define APOLLO_HEXAGON_DMA_STRESS_BYTES 131072
#define APOLLO_HEXAGON_DMA_STRESS_SEGMENTS 8
#define APOLLO_HEXAGON_APKO_MAGIC 0x4f4b5041
#define APOLLO_HEXAGON_APKO_ABI_VERSION 0
#define APOLLO_HEXAGON_GENERIC_ABI_VERSION 1
#define APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0 1
#define APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0_BIT \
	(1u << APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0)
#define APOLLO_HEXAGON_EXEC_KIND_CNN 1
#define APOLLO_HEXAGON_EXEC_KIND_VADD 2
#define APOLLO_HEXAGON_FAULT_CODE_JOB_FAILED 1
#define APOLLO_HEXAGON_GET_FAULT_FLAG_CLEAR 1
#define APOLLO_HEXAGON_FENCE_MODEL_ASYNC_IRQ_POLL 1
#define APOLLO_HEXAGON_BO_BIND_USAGE_READ 1
#define APOLLO_HEXAGON_BO_BIND_USAGE_WRITE 2
#define APOLLO_HEXAGON_BO_BIND_USAGE_EXEC 4
#define APOLLO_HEXAGON_BO_BIND_USAGE_MASK \
	(APOLLO_HEXAGON_BO_BIND_USAGE_READ | \
	 APOLLO_HEXAGON_BO_BIND_USAGE_WRITE | \
	 APOLLO_HEXAGON_BO_BIND_USAGE_EXEC)
#define APOLLO_HEXAGON_CMDQ_PACKET_WORDS 8
#define APOLLO_HEXAGON_CMDQ_PACKET_BYTES \
	(APOLLO_HEXAGON_CMDQ_PACKET_WORDS * sizeof(uint32_t))
#define APOLLO_HEXAGON_CMDQ_SUBMIT_MAX_PACKETS 2
#define APOLLO_HEXAGON_CMDQ_SUBMIT_MAX_BYTES \
	(APOLLO_HEXAGON_CMDQ_SUBMIT_MAX_PACKETS * \
	 APOLLO_HEXAGON_CMDQ_PACKET_BYTES)
#define APOLLO_HEXAGON_CMDQ_OPCODE_NOP 0
#define APOLLO_HEXAGON_CMDQ_OPCODE_COPY 1
#define APOLLO_HEXAGON_CMDQ_OPCODE_BARRIER 2
#define APOLLO_HEXAGON_CMDQ_OPCODE_SIGNAL_FENCE 3
#define APOLLO_HEXAGON_CMDQ_OPCODE_DISPATCH 4
#define APOLLO_HEXAGON_CMDQ_OPCODE_LOAD_EXECUTABLE 5
#define APOLLO_HEXAGON_CMDQ_DISPATCH_EXEC_SLOT_FLAG 0x80000000u
#define APOLLO_HEXAGON_CMDQ_EXEC_SLOT_MAX 15
#define APOLLO_HEXAGON_CMDQ_DISPATCH_KIND_VADD 2
#define APOLLO_HEXAGON_CMDQ_STATUS_DONE 1
#define APOLLO_HEXAGON_CMDQ_STATUS_ERROR 2
#define APOLLO_HEXAGON_CMDQ_FAULT_NONE 0
#define APOLLO_HEXAGON_CMDQ_FAULT_EMPTY 1
#define APOLLO_HEXAGON_CMDQ_FAULT_DISABLED 2
#define APOLLO_HEXAGON_CMDQ_FAULT_UNSUPPORTED_PACKET 3
#define APOLLO_HEXAGON_CMDQ_FAULT_MALFORMED_PACKET 4
#define APOLLO_HEXAGON_CMDQ_FAULT_DMA_ERROR 5

struct drm_apollo_hexagon_apko_header {
	uint32_t magic;
	uint32_t header_bytes;
	uint32_t abi_version;
	uint32_t executable_format;
	uint32_t entry_kind;
	uint32_t input_bytes;
	uint32_t output_bytes;
	uint32_t reserved[5];
};

#define DRM_IOCTL_BASE 'd'
#define DRM_COMMAND_BASE 0x40
#define DRM_IOWR(nr, type) _IOWR(DRM_IOCTL_BASE, nr, type)

struct drm_apollo_hexagon_query {
	uint32_t stream_id;
	uint32_t queue_count;
	uint32_t capabilities;
	uint32_t dma_path;
	uint32_t primary_endpoint;
	uint32_t pad;
};

struct drm_apollo_hexagon_query_caps {
	uint32_t size;
	uint32_t flags;
	uint32_t generic_abi_version;
	uint32_t supported_executable_formats;
	uint32_t max_command_bytes;
	uint32_t max_bindings_per_dispatch;
	uint32_t max_queue_count;
	uint32_t max_queue_depth;
	uint32_t fence_model;
	uint32_t smmu_page_granularity;
	uint32_t coherency_flags;
	uint32_t fault_record_size;
	uint32_t reserved[4];
};

struct drm_apollo_hexagon_context_create {
	uint32_t size;
	uint32_t flags;
	uint32_t generic_abi_version;
	uint32_t handle;
	uint32_t queue_count;
	uint32_t fence_model;
	uint32_t reserved[4];
};

struct drm_apollo_hexagon_context_destroy {
	uint32_t handle;
	uint32_t pad;
};

struct drm_apollo_hexagon_bo_create {
	uint32_t size;
	uint32_t flags;
	uint64_t bo_size;
	uint32_t handle;
	uint32_t pad;
	uint64_t mmap_offset;
	uint32_t reserved[4];
};

struct drm_apollo_hexagon_bo_destroy {
	uint32_t handle;
	uint32_t pad;
};

struct drm_apollo_hexagon_bo_bind {
	uint32_t size;
	uint32_t flags;
	uint32_t context_handle;
	uint32_t bo_handle;
	uint64_t offset;
	uint64_t length;
	uint64_t iova;
	uint32_t bind_handle;
	uint32_t usage;
	uint32_t reserved[4];
};

struct drm_apollo_hexagon_bo_unbind {
	uint32_t size;
	uint32_t flags;
	uint32_t context_handle;
	uint32_t bind_handle;
	uint32_t reserved[2];
};

struct drm_apollo_hexagon_cnn_job {
	uint32_t input[APOLLO_HEXAGON_CNN_INPUT_WORDS];
	uint32_t output[APOLLO_HEXAGON_CNN_OUTPUT_WORDS];
	uint32_t status;
	uint32_t flags;
	uint32_t queue_id;
	uint32_t fence_seq;
};

struct drm_apollo_hexagon_vadd_job {
	uint32_t lhs[APOLLO_HEXAGON_VADD_WORDS];
	uint32_t rhs[APOLLO_HEXAGON_VADD_WORDS];
	uint32_t output[APOLLO_HEXAGON_VADD_OUTPUT_WORDS];
	uint32_t status;
	uint32_t flags;
	uint32_t queue_id;
	uint32_t fence_seq;
};

struct drm_apollo_hexagon_dma_stress_job {
	uint32_t bytes;
	uint32_t segment_bytes;
	uint32_t seed;
	uint32_t checksum;
	uint32_t status;
	uint32_t flags;
	uint32_t queue_id;
	uint32_t fence_seq;
};

struct drm_apollo_hexagon_exec_create {
	uint32_t size;
	uint32_t flags;
	uint64_t data_ptr;
	uint32_t data_size;
	uint32_t handle;
	uint32_t executable_format;
	uint32_t abi_version;
	uint32_t entry_kind;
	uint32_t input_bytes;
	uint32_t output_bytes;
	uint32_t reserved[4];
};

struct drm_apollo_hexagon_exec_destroy {
	uint32_t handle;
	uint32_t pad;
};

struct drm_apollo_hexagon_submit {
	uint32_t size;
	uint32_t flags;
	uint32_t executable_handle;
	uint32_t queue_id;
	uint64_t input_ptr;
	uint64_t output_ptr;
	uint32_t input_bytes;
	uint32_t output_bytes;
	uint32_t status;
	uint32_t fence_seq;
	uint32_t reserved[4];
};

struct drm_apollo_hexagon_cmd_submit {
	uint32_t size;
	uint32_t flags;
	uint32_t context_handle;
	uint32_t command_bo_handle;
	uint64_t command_offset;
	uint32_t command_size;
	uint32_t queue_id;
	uint32_t status;
	uint32_t result;
	uint32_t fence_seq;
	uint32_t reserved[4];
};

struct drm_apollo_hexagon_fault {
	uint32_t size;
	uint32_t flags;
	uint32_t queue_id;
	uint32_t code;
	uint32_t status;
	uint32_t result;
	uint32_t fence_seq;
	uint32_t reserved[5];
};

struct drm_apollo_hexagon_wait {
	uint32_t size;
	uint32_t flags;
	uint32_t queue_id;
	uint32_t fence_seq;
	uint64_t timeout_ns;
	uint32_t status;
	uint32_t result;
	uint32_t current_fence_seq;
	uint32_t reserved[3];
};

enum drm_apollo_hexagon_ioctl_id {
	DRM_APOLLO_HEXAGON_QUERY = 0,
	DRM_APOLLO_HEXAGON_SUBMIT_CNN,
	DRM_APOLLO_HEXAGON_SUBMIT_VADD,
	DRM_APOLLO_HEXAGON_DMA_STRESS,
	DRM_APOLLO_HEXAGON_EXEC_CREATE,
	DRM_APOLLO_HEXAGON_EXEC_DESTROY,
	DRM_APOLLO_HEXAGON_SUBMIT,
	DRM_APOLLO_HEXAGON_GET_FAULT,
	DRM_APOLLO_HEXAGON_QUERY_CAPS,
	DRM_APOLLO_HEXAGON_CONTEXT_CREATE,
	DRM_APOLLO_HEXAGON_CONTEXT_DESTROY,
	DRM_APOLLO_HEXAGON_BO_CREATE,
	DRM_APOLLO_HEXAGON_BO_DESTROY,
	DRM_APOLLO_HEXAGON_WAIT,
	DRM_APOLLO_HEXAGON_BO_BIND,
	DRM_APOLLO_HEXAGON_BO_UNBIND,
	DRM_APOLLO_HEXAGON_CMD_SUBMIT,
};

#define DRM_IOCTL_APOLLO_HEXAGON_QUERY \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_QUERY, \
		 struct drm_apollo_hexagon_query)
#define DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_CNN \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_SUBMIT_CNN, \
		 struct drm_apollo_hexagon_cnn_job)
#define DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_VADD \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_SUBMIT_VADD, \
		 struct drm_apollo_hexagon_vadd_job)
#define DRM_IOCTL_APOLLO_HEXAGON_DMA_STRESS \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_DMA_STRESS, \
		 struct drm_apollo_hexagon_dma_stress_job)
#define DRM_IOCTL_APOLLO_HEXAGON_EXEC_CREATE \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_EXEC_CREATE, \
		 struct drm_apollo_hexagon_exec_create)
#define DRM_IOCTL_APOLLO_HEXAGON_EXEC_DESTROY \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_EXEC_DESTROY, \
		 struct drm_apollo_hexagon_exec_destroy)
#define DRM_IOCTL_APOLLO_HEXAGON_SUBMIT \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_SUBMIT, \
		 struct drm_apollo_hexagon_submit)
#define DRM_IOCTL_APOLLO_HEXAGON_GET_FAULT \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_GET_FAULT, \
		 struct drm_apollo_hexagon_fault)
#define DRM_IOCTL_APOLLO_HEXAGON_QUERY_CAPS \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_QUERY_CAPS, \
		 struct drm_apollo_hexagon_query_caps)
#define DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_CREATE \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_CONTEXT_CREATE, \
		 struct drm_apollo_hexagon_context_create)
#define DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_DESTROY \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_CONTEXT_DESTROY, \
		 struct drm_apollo_hexagon_context_destroy)
#define DRM_IOCTL_APOLLO_HEXAGON_BO_CREATE \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_BO_CREATE, \
		 struct drm_apollo_hexagon_bo_create)
#define DRM_IOCTL_APOLLO_HEXAGON_BO_DESTROY \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_BO_DESTROY, \
		 struct drm_apollo_hexagon_bo_destroy)
#define DRM_IOCTL_APOLLO_HEXAGON_WAIT \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_WAIT, \
		 struct drm_apollo_hexagon_wait)
#define DRM_IOCTL_APOLLO_HEXAGON_BO_BIND \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_BO_BIND, \
		 struct drm_apollo_hexagon_bo_bind)
#define DRM_IOCTL_APOLLO_HEXAGON_BO_UNBIND \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_BO_UNBIND, \
		 struct drm_apollo_hexagon_bo_unbind)
#define DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT \
	DRM_IOWR(DRM_COMMAND_BASE + DRM_APOLLO_HEXAGON_CMD_SUBMIT, \
		 struct drm_apollo_hexagon_cmd_submit)

#endif /* APOLLO_HEXAGON_UAPI_GUEST_H */
