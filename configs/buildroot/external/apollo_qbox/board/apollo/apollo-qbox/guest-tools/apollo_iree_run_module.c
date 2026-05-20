// SPDX-License-Identifier: MIT
/*
 * Minimal iree-run-module compatible Apollo HAL registry frontend.
 *
 * This is intentionally small and explicit: it accepts the subset of
 * iree-run-module options used by the QBox tiny-CNN fixture, requires
 * --device=apollo-hexagon for Apollo execution, rejects CPU fallback devices,
 * and routes execution through the registered Apollo HAL device instead of the
 * legacy repo-local dlopen runner path.
 */

#include "apollo_iree_hal_registry.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define APOLLO_HEXAGON_STRESS_SEED 0x13579bdfu

struct options {
	const char *device_name;
	const char *device_path;
	const char *plugin_path;
	const char *metadata;
	const char *module;
	const char *function;
	const char *input;
	int list_drivers;
	int dump_devices;
	int skip_stress;
	int stress_only;
};

static void usage(const char *argv0)
{
	fprintf(stderr,
		"usage: %s --device=apollo-hexagon --module=PATH "
		"--function=tiny_cnn_graph|vector_add_graph|mnist_graph "
		"[--metadata PATH] "
		"[--executable_plugin PATH] [--apollo-device PATH] "
		"[--list_drivers] [--dump_devices] "
		"[--skip-stress] [--stress-only]\n",
		argv0);
}

static int arg_value(int argc, char **argv, int *index, const char *name,
		     const char **out)
{
	size_t len = strlen(name);
	const char *arg = argv[*index];

	if (strncmp(arg, name, len) != 0)
		return 0;
	if (arg[len] == '=') {
		*out = arg + len + 1;
		return 1;
	}
	if (arg[len] != '\0')
		return 0;
	if (*index + 1 >= argc)
		return -EINVAL;
	*out = argv[++(*index)];
	return 1;
}

static float word_to_float(uint32_t word)
{
	float value;

	memcpy(&value, &word, sizeof(value));
	return value;
}

static int parse_args(int argc, char **argv, struct options *opts)
{
	int i;

	memset(opts, 0, sizeof(*opts));
	opts->device_path = getenv("APOLLO_HEXAGON_DEV");

	for (i = 1; i < argc; i++) {
		int matched;

		matched = arg_value(argc, argv, &i, "--device", &opts->device_name);
		if (matched < 0)
			return matched;
		if (matched)
			continue;
		matched = arg_value(argc, argv, &i, "--module", &opts->module);
		if (matched < 0)
			return matched;
		if (matched)
			continue;
		matched = arg_value(argc, argv, &i, "--metadata", &opts->metadata);
		if (matched < 0)
			return matched;
		if (matched)
			continue;
		matched = arg_value(argc, argv, &i, "--executable_plugin",
				    &opts->plugin_path);
		if (matched < 0)
			return matched;
		if (matched)
			continue;
		matched = arg_value(argc, argv, &i, "--plugin",
				    &opts->plugin_path);
		if (matched < 0)
			return matched;
		if (matched)
			continue;
		matched = arg_value(argc, argv, &i, "--function", &opts->function);
		if (matched < 0)
			return matched;
		if (matched)
			continue;
		matched = arg_value(argc, argv, &i, "--input", &opts->input);
		if (matched < 0)
			return matched;
		if (matched)
			continue;
		matched = arg_value(argc, argv, &i, "--apollo-device",
				    &opts->device_path);
		if (matched < 0)
			return matched;
		if (matched)
			continue;
		if (strcmp(argv[i], "--list_drivers") == 0) {
			opts->list_drivers = 1;
			continue;
		}
		if (strcmp(argv[i], "--dump_devices") == 0) {
			opts->dump_devices = 1;
			continue;
		}
		if (strcmp(argv[i], "--skip-stress") == 0) {
			opts->skip_stress = 1;
			continue;
		}
		if (strcmp(argv[i], "--stress-only") == 0) {
			opts->stress_only = 1;
			continue;
		}
		usage(argv[0]);
		return -EINVAL;
	}
	return 0;
}

static const char *apollo_device_name(const char *device_name)
{
	if (!device_name || !device_name[0])
		return "apollo-hexagon";
	if (strcmp(device_name, "apollo-hexagon://0") == 0)
		return "apollo-hexagon";
	return device_name;
}

static void print_hal_boundary_guard(void)
{
	printf("IREE Apollo Hexagon HAL: integration_status=repo-local-registry-frontend\n");
	printf("IREE Apollo Hexagon HAL: upstream_hal_driver=not-linked\n");
	printf("IREE Apollo Hexagon HAL: blocker=apollo-hexagon is not registered in the upstream IREE runtime HAL driver registry; VMFB APKO trailer evidence is transitional only\n");
}

static int handle_query_options(const struct options *opts)
{
	const struct apollo_iree_hal_device *device;
	const char *device_name;
	char error[256];

	if (opts->list_drivers) {
		printf("IREE HAL drivers:\n");
		printf("  apollo-hexagon (Apollo QBox repo-local C HAL registry frontend)\n");
		print_hal_boundary_guard();
	}

	if (!opts->dump_devices)
		return 0;

	device_name = apollo_device_name(opts->device_name);
	device = apollo_iree_hal_registry_lookup(device_name, opts->plugin_path,
						 error, sizeof(error));
	if (!device) {
		fprintf(stderr, "%s\n", error);
		return 1;
	}

	printf("IREE Apollo Hexagon HAL: device[0]=apollo-hexagon://0\n");
	printf("IREE Apollo Hexagon HAL: device=%s\n", device->name);
	printf("IREE Apollo Hexagon HAL: description=%s\n",
	       device->description);
	printf("IREE Apollo Hexagon HAL: dynamically registered C HAL plugin=%s driver=%s api=%u\n",
	       device->plugin_path, device->ops->name,
	       device->ops->api_version);
	print_hal_boundary_guard();
	apollo_iree_hal_registry_unload_plugin();
	return 0;
}

static void close_apollo_executable(struct apollo_hexagon_executable *exe)
{
	apollo_iree_hal_registry_unload_plugin();
	apollo_hexagon_unload_executable(exe);
}

static void close_apollo_device(
	const struct apollo_iree_hal_device *device,
	struct apollo_hexagon_queue *queue,
	struct apollo_hexagon_executable *exe)
{
	if (device && device->ops && device->ops->queue_close)
		device->ops->queue_close(queue);
	close_apollo_executable(exe);
}

int main(int argc, char **argv)
{
	const struct apollo_iree_hal_device *device;
	struct apollo_hexagon_executable exe;
	struct apollo_hexagon_command_buffer cmd;
	struct apollo_hexagon_vadd_command_buffer vadd_cmd;
	struct apollo_hexagon_fence fence;
	struct apollo_hexagon_queue queue;
	struct options opts;
	char error[256];
	uint32_t checksum = 0;
	int ret;
	int i;

	ret = parse_args(argc, argv, &opts);
	if (ret) {
		if (ret == -EINVAL)
			return 2;
		return 1;
	}

	opts.device_name = apollo_device_name(opts.device_name);
	if (opts.list_drivers || opts.dump_devices)
		return handle_query_options(&opts);

	ret = apollo_hexagon_load_executable(opts.metadata, opts.module, &exe,
					       error, sizeof(error));
	if (ret) {
		fprintf(stderr, "%s: %s\n", error, strerror(-ret));
		return 1;
	}
	if (opts.plugin_path && opts.plugin_path[0]) {
		ret = snprintf(exe.plugin_path, sizeof(exe.plugin_path), "%s",
			       opts.plugin_path);
		if (ret < 0 || (size_t)ret >= sizeof(exe.plugin_path)) {
			fprintf(stderr, "Apollo HAL plugin path is too long\n");
			apollo_hexagon_unload_executable(&exe);
			return 1;
		}
	}
	if (opts.function && opts.function[0] &&
	    strcmp(opts.function, exe.entry_point) != 0) {
		fprintf(stderr, "Apollo HAL device %s rejects executable entry %s\n",
			opts.device_name, opts.function);
		apollo_hexagon_unload_executable(&exe);
		return 1;
	}

	device = apollo_iree_hal_registry_lookup(opts.device_name,
						 exe.plugin_path, error,
						 sizeof(error));
	if (!device) {
		fprintf(stderr, "%s\n", error);
		apollo_hexagon_unload_executable(&exe);
		return 1;
	}

	ret = apollo_iree_hal_registry_open_queue(device, &queue,
						 opts.device_path, error,
						 sizeof(error));
	if (ret) {
		fprintf(stderr, "%s: %s\n", error, strerror(-ret));
		close_apollo_executable(&exe);
		return 1;
	}

	printf("IREE Apollo Hexagon HAL: device=%s\n", device->name);
	printf("IREE Apollo Hexagon HAL: drm-accel device=%s\n",
	       queue.device);
	printf("IREE Apollo Hexagon HAL: upstream-style HAL registry device=%s driver=%s\n",
	       device->name, device->ops->name);
	printf("IREE Apollo Hexagon HAL: dynamically registered C HAL plugin=%s driver=%s api=%u\n",
	       device->plugin_path, device->ops->name, device->ops->api_version);
	printf("IREE Apollo Hexagon HAL: executable=%s entry=%s bytes=%zu\n",
	       exe.module_path, exe.entry_point, exe.module_size);
	if (exe.executable_format == APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0)
		printf("IREE Apollo Hexagon HAL: executable_format=apollo-hexagon-apko-v0 apko=%s bytes=%zu\n",
		       exe.apko_path, exe.apko_size);
	if (exe.apko_embedded)
		printf("IREE Apollo Hexagon HAL: executable_source=vmfb-embedded-apko\n");
	if (exe.compiler_name[0])
		printf("IREE Apollo Hexagon HAL: compiler bridge=%s artifact=%s bytes=%zu\n",
		       exe.compiler_name, exe.compiler_artifact_path,
		       exe.compiler_artifact_size);
	printf("IREE Apollo Hexagon HAL: executable_plugin compatibility export=%s staged\n",
	       "iree_hal_executable_plugin_query");
	printf("IREE Apollo Hexagon HAL: queues=%u command-buffer=%s fence=async-irq-poll\n",
	       queue.queue_count,
	       exe.executable_format == APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0 ?
	       "generic-submit" : "fixed");
	printf("IREE Apollo Hexagon HAL: generic_abi_version=%u executable_formats=0x%08x max_command_bytes=%u max_bindings_per_dispatch=%u max_queue_depth=%u fault_record_size=%u\n",
	       queue.generic_abi_version, queue.supported_executable_formats,
	       queue.max_command_bytes, queue.max_bindings_per_dispatch,
	       queue.max_queue_depth, queue.fault_record_size);
	(void)opts.input;

	if (!opts.skip_stress) {
		memset(&fence, 0, sizeof(fence));
		device->ops->queue_select(&queue, 0);
		ret = device->ops->queue_submit_dma_stress(&queue,
			APOLLO_HEXAGON_DMA_STRESS_BYTES,
			APOLLO_HEXAGON_STRESS_SEED, &checksum, &fence, error,
			sizeof(error));
		if (ret) {
			fprintf(stderr, "%s: %s\n", error, strerror(-ret));
			close_apollo_device(device, &queue, &exe);
			return 1;
		}
		printf("IREE Apollo Hexagon HAL: SG DMA stress ok queue=%u bytes=%u segments=%u checksum=0x%08x\n",
		       fence.queue_id, APOLLO_HEXAGON_DMA_STRESS_BYTES,
		       APOLLO_HEXAGON_DMA_STRESS_SEGMENTS, checksum);
		printf("IREE Apollo Hexagon HAL: async fence signaled queue=%u fence=%u status=0x%08x\n",
		       fence.queue_id, fence.fence_seq, fence.status);
	}

	if (opts.stress_only) {
		close_apollo_device(device, &queue, &exe);
		return 0;
	}

	if (strcmp(exe.entry_point, "vector_add_graph") == 0) {
		memset(&vadd_cmd, 0, sizeof(vadd_cmd));
		for (i = 0; i < APOLLO_HEXAGON_VADD_WORDS; i++) {
			vadd_cmd.lhs[i] = (uint32_t)i + 1;
			vadd_cmd.rhs[i] = ((uint32_t)i + 1) * 10;
		}

		memset(&fence, 0, sizeof(fence));
		device->ops->queue_select(&queue, 1);
		if (exe.executable_format ==
		    APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0) {
			uint32_t input[APOLLO_HEXAGON_VADD_INPUT_WORDS];

			memcpy(input, vadd_cmd.lhs, sizeof(vadd_cmd.lhs));
			memcpy(input + APOLLO_HEXAGON_VADD_WORDS, vadd_cmd.rhs,
			       sizeof(vadd_cmd.rhs));
			ret = device->ops->queue_submit_apko(
				&queue, &exe, input, sizeof(input),
				vadd_cmd.output, sizeof(vadd_cmd.output),
				&fence, error, sizeof(error));
			vadd_cmd.status = fence.status;
		} else {
			ret = device->ops->queue_submit_vadd(
				&queue, &vadd_cmd, &fence, error,
				sizeof(error));
		}
		if (ret) {
			fprintf(stderr, "%s: %s\n", error, strerror(-ret));
			close_apollo_device(device, &queue, &exe);
			return 1;
		}
		close_apollo_device(device, &queue, &exe);

		printf("IREE Apollo Hexagon HAL: command buffer submitted\n");
		printf("IREE Apollo Hexagon HAL: offload complete queue=%u status=0x%08x\n",
		       fence.queue_id, vadd_cmd.status);
		printf("IREE Apollo Hexagon HAL: async fence signaled queue=%u fence=%u status=0x%08x\n",
		       fence.queue_id, fence.fence_seq, fence.status);
		printf("EXEC @%s [apollo-hexagon]\n", exe.entry_point);
		printf("result[0]: hal.buffer_view\n");
		printf("4xf32=%.0f %.0f %.0f %.0f\n",
		       word_to_float(vadd_cmd.output[0]),
		       word_to_float(vadd_cmd.output[1]),
		       word_to_float(vadd_cmd.output[2]),
		       word_to_float(vadd_cmd.output[3]));
		return 0;
	}

	if (strcmp(exe.entry_point, "mnist_graph") == 0) {
		uint32_t input[APOLLO_HEXAGON_MNIST_INPUT_WORDS];
		uint32_t output[APOLLO_HEXAGON_MNIST_OUTPUT_WORDS] = { 0 };

		for (i = 0; i < APOLLO_HEXAGON_MNIST_INPUT_WORDS; i++)
			input[i] = 0;

		memset(&fence, 0, sizeof(fence));
		device->ops->queue_select(&queue, 1);
		if (exe.executable_format != APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0) {
			fprintf(stderr, "MNIST APKO metadata is required\n");
			close_apollo_device(device, &queue, &exe);
			return 1;
		}
		ret = device->ops->queue_submit_apko(
			&queue, &exe, input, sizeof(input), output, sizeof(output),
			&fence, error, sizeof(error));
		if (ret) {
			fprintf(stderr, "%s: %s\n", error, strerror(-ret));
			close_apollo_device(device, &queue, &exe);
			return 1;
		}
		close_apollo_device(device, &queue, &exe);

		printf("IREE Apollo Hexagon HAL: command buffer submitted\n");
		printf("IREE Apollo Hexagon HAL: offload complete queue=%u status=0x%08x\n",
		       fence.queue_id, fence.status);
		printf("IREE Apollo Hexagon HAL: async fence signaled queue=%u fence=%u status=0x%08x\n",
		       fence.queue_id, fence.fence_seq, fence.status);
		printf("EXEC @%s [apollo-hexagon]\n", exe.entry_point);
		printf("result[0]: hal.buffer_view\n");
		printf("1x10xf32=[%.0f %.0f %.0f %.0f %.0f %.0f %.0f %.0f %.0f %.0f]\n",
		       word_to_float(output[0]), word_to_float(output[1]),
		       word_to_float(output[2]), word_to_float(output[3]),
		       word_to_float(output[4]), word_to_float(output[5]),
		       word_to_float(output[6]), word_to_float(output[7]),
		       word_to_float(output[8]), word_to_float(output[9]));
		return 0;
	}

	memset(&cmd, 0, sizeof(cmd));
	for (i = 0; i < APOLLO_HEXAGON_CNN_INPUT_WORDS; i++)
		cmd.input[i] = (uint32_t)i + 1;

	memset(&fence, 0, sizeof(fence));
	device->ops->queue_select(&queue, 1);
	if (exe.executable_format == APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0) {
		ret = device->ops->queue_submit_apko(
			&queue, &exe, cmd.input, sizeof(cmd.input), cmd.output,
			sizeof(cmd.output), &fence, error, sizeof(error));
		cmd.status = fence.status;
	} else {
		ret = device->ops->queue_submit_cnn(&queue, &cmd, &fence, error,
						    sizeof(error));
	}
	if (ret) {
		fprintf(stderr, "%s: %s\n", error, strerror(-ret));
		close_apollo_device(device, &queue, &exe);
		return 1;
	}
	close_apollo_device(device, &queue, &exe);

	printf("IREE Apollo Hexagon HAL: command buffer submitted\n");
	printf("IREE Apollo Hexagon HAL: offload complete queue=%u status=0x%08x\n",
	       fence.queue_id, cmd.status);
	printf("IREE Apollo Hexagon HAL: async fence signaled queue=%u fence=%u status=0x%08x\n",
	       fence.queue_id, fence.fence_seq, fence.status);
	printf("EXEC @%s [apollo-hexagon]\n", exe.entry_point);
	printf("result[0]: hal.buffer_view\n");
	printf("1x1x2x2xf32=[[[%.0f %.0f][%.0f %.0f]]]\n",
	       word_to_float(cmd.output[0]), word_to_float(cmd.output[1]),
	       word_to_float(cmd.output[2]), word_to_float(cmd.output[3]));

	return 0;
}
