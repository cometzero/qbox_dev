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

enum drm_apollo_hexagon_ioctl_id {
	DRM_APOLLO_HEXAGON_QUERY = 0,
	DRM_APOLLO_HEXAGON_SUBMIT_CNN,
	DRM_APOLLO_HEXAGON_SUBMIT_VADD,
	DRM_APOLLO_HEXAGON_DMA_STRESS,
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

#endif /* APOLLO_HEXAGON_UAPI_GUEST_H */
