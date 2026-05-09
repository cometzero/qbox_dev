// SPDX-License-Identifier: MIT
/*
 * Minimal Apollo Hexagon functional HAL runner.
 *
 * This intentionally keeps the guest-side ABI tiny: it submits the canonical
 * tiny CNN fixture to /dev/apollo-hexagon and prints an IREE run-module-like
 * result so the QBox guest smoke can validate accelerator offload end to end.
 */

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define APOLLO_HEXAGON_CNN_INPUT_WORDS 16
#define APOLLO_HEXAGON_CNN_OUTPUT_WORDS 4

struct apollo_hexagon_cnn_job {
	uint32_t input[APOLLO_HEXAGON_CNN_INPUT_WORDS];
	uint32_t output[APOLLO_HEXAGON_CNN_OUTPUT_WORDS];
	uint32_t status;
	uint32_t flags;
};

#define APOLLO_HEXAGON_IOC_MAGIC 'H'
#define APOLLO_HEXAGON_IOC_SUBMIT_CNN \
	_IOWR(APOLLO_HEXAGON_IOC_MAGIC, 0x01, struct apollo_hexagon_cnn_job)

static float word_to_float(uint32_t word)
{
	float value;

	memcpy(&value, &word, sizeof(value));
	return value;
}

int main(int argc, char **argv)
{
	const char *device = getenv("APOLLO_HEXAGON_DEV");
	struct apollo_hexagon_cnn_job job = { 0 };
	int fd;
	int ret;
	int i;

	(void)argc;
	(void)argv;

	if (!device || !device[0])
		device = "/dev/apollo-hexagon";

	for (i = 0; i < APOLLO_HEXAGON_CNN_INPUT_WORDS; i++)
		job.input[i] = i + 1;

	fd = open(device, O_RDWR | O_CLOEXEC);
	if (fd < 0) {
		fprintf(stderr, "failed to open %s: %s\n", device,
			strerror(errno));
		return 1;
	}

	ret = ioctl(fd, APOLLO_HEXAGON_IOC_SUBMIT_CNN, &job);
	if (ret < 0) {
		fprintf(stderr, "APOLLO_HEXAGON_IOC_SUBMIT_CNN failed: %s\n",
			strerror(errno));
		close(fd);
		return 1;
	}

	close(fd);

	printf("IREE Apollo Hexagon HAL: device=apollo-hexagon\n");
	printf("IREE Apollo Hexagon HAL: offload complete status=0x%08x\n",
	       job.status);
	printf("EXEC @tiny_cnn_graph [apollo-hexagon]\n");
	printf("result[0]: hal.buffer_view\n");
	printf("1x1x2x2xf32=[[[%.0f %.0f][%.0f %.0f]]]\n",
	       word_to_float(job.output[0]), word_to_float(job.output[1]),
	       word_to_float(job.output[2]), word_to_float(job.output[3]));

	return 0;
}
