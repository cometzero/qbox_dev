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

struct apollo_hexagon_cnn_job {
	uint32_t input[APOLLO_HEXAGON_CNN_INPUT_WORDS];
	uint32_t output[APOLLO_HEXAGON_CNN_OUTPUT_WORDS];
	uint32_t status;
	uint32_t flags;
	uint32_t queue_id;
	uint32_t fence_seq;
};

struct apollo_hexagon_vadd_job {
	uint32_t lhs[APOLLO_HEXAGON_VADD_WORDS];
	uint32_t rhs[APOLLO_HEXAGON_VADD_WORDS];
	uint32_t output[APOLLO_HEXAGON_VADD_OUTPUT_WORDS];
	uint32_t status;
	uint32_t flags;
	uint32_t queue_id;
	uint32_t fence_seq;
};

struct apollo_hexagon_dma_stress_job {
	uint32_t bytes;
	uint32_t segment_bytes;
	uint32_t seed;
	uint32_t checksum;
	uint32_t status;
	uint32_t flags;
	uint32_t queue_id;
	uint32_t fence_seq;
};

#define APOLLO_HEXAGON_IOC_MAGIC 'H'
#define APOLLO_HEXAGON_IOC_SUBMIT_CNN \
	_IOWR(APOLLO_HEXAGON_IOC_MAGIC, 0x01, struct apollo_hexagon_cnn_job)
#define APOLLO_HEXAGON_IOC_DMA_STRESS \
	_IOWR(APOLLO_HEXAGON_IOC_MAGIC, 0x02, \
	      struct apollo_hexagon_dma_stress_job)
#define APOLLO_HEXAGON_IOC_SUBMIT_VADD \
	_IOWR(APOLLO_HEXAGON_IOC_MAGIC, 0x03, struct apollo_hexagon_vadd_job)

#endif /* APOLLO_HEXAGON_UAPI_GUEST_H */
