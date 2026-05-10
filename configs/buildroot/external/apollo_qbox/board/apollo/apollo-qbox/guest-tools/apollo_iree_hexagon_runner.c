// SPDX-License-Identifier: MIT
/*
 * Apollo Hexagon repo-local IREE HAL runner.
 *
 * The runner models the production HAL layers that are useful in QBox today:
 * executable metadata loading, command buffer recording, synchronous queue
 * submission, dynamic C HAL plugin loading, and host-visible fence completion.
 */

#include "apollo_iree_hexagon_hal.h"
#include "apollo_iree_hexagon_plugin.h"

#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define APOLLO_HEXAGON_STRESS_SEED 0x13579bdfu

struct hal_binding {
	const struct apollo_iree_hexagon_plugin_v1 *ops;
	void *dl_handle;
	int dynamic;
};

static int direct_queue_open(struct apollo_hexagon_queue *queue,
			     const char *device, char *error, size_t error_len)
{
	return apollo_hexagon_queue_open(queue, device, error, error_len);
}

static void direct_queue_close(struct apollo_hexagon_queue *queue)
{
	apollo_hexagon_queue_close(queue);
}

static void direct_queue_select(struct apollo_hexagon_queue *queue,
				uint32_t queue_id)
{
	apollo_hexagon_queue_select(queue, queue_id);
}

static int direct_queue_submit_cnn(struct apollo_hexagon_queue *queue,
				   struct apollo_hexagon_command_buffer *cmd,
				   struct apollo_hexagon_fence *fence,
				   char *error, size_t error_len)
{
	return apollo_hexagon_queue_submit_cnn(queue, cmd, fence, error,
					       error_len);
}

static int direct_queue_submit_dma_stress(struct apollo_hexagon_queue *queue,
					  uint32_t bytes, uint32_t seed,
					  uint32_t *checksum,
					  struct apollo_hexagon_fence *fence,
					  char *error, size_t error_len)
{
	return apollo_hexagon_queue_submit_dma_stress(queue, bytes, seed,
						      checksum, fence, error,
						      error_len);
}

static const struct apollo_iree_hexagon_plugin_v1 direct_ops = {
	.api_version = APOLLO_IREE_HEXAGON_PLUGIN_API_VERSION,
	.name = "apollo-hexagon-hal-direct",
	.description = "Apollo QBox Hexagon direct HAL fallback",
	.queue_open = direct_queue_open,
	.queue_close = direct_queue_close,
	.queue_select = direct_queue_select,
	.queue_submit_cnn = direct_queue_submit_cnn,
	.queue_submit_dma_stress = direct_queue_submit_dma_stress,
};

static int load_hal_plugin(const char *path, struct hal_binding *binding,
			   char *error, size_t error_len)
{
	apollo_iree_hexagon_plugin_query_fn_t query;

	binding->ops = &direct_ops;
	binding->dl_handle = NULL;
	binding->dynamic = 0;
	if (!path || !path[0])
		return 0;

	binding->dl_handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
	if (!binding->dl_handle) {
		snprintf(error, error_len, "failed to dlopen HAL plugin");
		return -EINVAL;
	}
	query = (apollo_iree_hexagon_plugin_query_fn_t)dlsym(
		binding->dl_handle, APOLLO_IREE_HEXAGON_PLUGIN_EXPORT_NAME);
	if (!query) {
		snprintf(error, error_len, "HAL plugin missing query export");
		dlclose(binding->dl_handle);
		binding->dl_handle = NULL;
		return -EINVAL;
	}
	binding->ops = query(APOLLO_IREE_HEXAGON_PLUGIN_API_VERSION);
	if (!binding->ops || !binding->ops->queue_open ||
	    !binding->ops->queue_submit_cnn ||
	    !binding->ops->queue_submit_dma_stress) {
		snprintf(error, error_len, "HAL plugin has incompatible ABI");
		dlclose(binding->dl_handle);
		binding->dl_handle = NULL;
		return -EINVAL;
	}
	binding->dynamic = 1;
	return 0;
}

static void unload_hal_plugin(struct hal_binding *binding)
{
	if (binding->dl_handle)
		dlclose(binding->dl_handle);
	binding->dl_handle = NULL;
	binding->ops = &direct_ops;
	binding->dynamic = 0;
}

static float word_to_float(uint32_t word)
{
	float value;

	memcpy(&value, &word, sizeof(value));
	return value;
}

static void usage(const char *argv0)
{
	fprintf(stderr,
		"usage: %s [--metadata PATH] [--module PATH] [--device PATH] "
		"[--plugin PATH] [--no-plugin] [--skip-stress] [--stress-only]\n",
		argv0);
}

int main(int argc, char **argv)
{
	const char *device = getenv("APOLLO_HEXAGON_DEV");
	const char *metadata = NULL;
	const char *module = NULL;
	const char *plugin = NULL;
	struct apollo_hexagon_executable exe;
	struct apollo_hexagon_command_buffer cmd;
	struct apollo_hexagon_queue queue;
	struct apollo_hexagon_fence fence;
	struct hal_binding binding;
	char error[256];
	uint32_t checksum = 0;
	int skip_stress = 0;
	int stress_only = 0;
	int no_plugin = 0;
	int ret;
	int i;

	if (!device || !device[0])
		device = "/dev/apollo-hexagon";

	for (i = 1; i < argc; i++) {
		if (strcmp(argv[i], "--metadata") == 0 && i + 1 < argc) {
			metadata = argv[++i];
		} else if (strcmp(argv[i], "--module") == 0 && i + 1 < argc) {
			module = argv[++i];
		} else if (strcmp(argv[i], "--device") == 0 && i + 1 < argc) {
			device = argv[++i];
		} else if (strcmp(argv[i], "--plugin") == 0 && i + 1 < argc) {
			plugin = argv[++i];
		} else if (strcmp(argv[i], "--no-plugin") == 0) {
			no_plugin = 1;
		} else if (strcmp(argv[i], "--skip-stress") == 0) {
			skip_stress = 1;
		} else if (strcmp(argv[i], "--stress-only") == 0) {
			stress_only = 1;
		} else {
			usage(argv[0]);
			return 2;
		}
	}

	if (!metadata)
		metadata = "apollo_hexagon.vmfb.meta";

	ret = apollo_hexagon_load_executable(metadata, module, &exe, error,
					       sizeof(error));
	if (ret) {
		fprintf(stderr, "%s: %s\n", error, strerror(-ret));
		return 1;
	}
	if (!plugin && !no_plugin)
		plugin = exe.plugin_path;

	ret = load_hal_plugin(plugin, &binding, error, sizeof(error));
	if (ret) {
		fprintf(stderr, "%s\n", error);
		return 1;
	}

	ret = binding.ops->queue_open(&queue, device, error, sizeof(error));
	if (ret) {
		fprintf(stderr, "%s: %s\n", error, strerror(-ret));
		unload_hal_plugin(&binding);
		return 1;
	}

	printf("IREE Apollo Hexagon HAL: device=apollo-hexagon\n");
	printf("IREE Apollo Hexagon HAL: executable=%s entry=%s bytes=%zu\n",
	       exe.module_path, exe.entry_point, exe.module_size);
	printf("IREE Apollo Hexagon HAL: dynamic C HAL plugin=%s name=%s api=%u\n",
	       binding.dynamic ? plugin : "direct-linked", binding.ops->name,
	       binding.ops->api_version);
	if (binding.dynamic)
		printf("IREE Apollo Hexagon HAL: upstream executable_plugin export=%s available\n",
		       "iree_hal_executable_plugin_query");
	printf("IREE Apollo Hexagon HAL: queues=2 command-buffer=fixed fence=async-irq-poll\n");

	if (!skip_stress) {
		memset(&fence, 0, sizeof(fence));
		binding.ops->queue_select(&queue, 0);
		ret = binding.ops->queue_submit_dma_stress(&queue,
			APOLLO_HEXAGON_DMA_STRESS_BYTES,
			APOLLO_HEXAGON_STRESS_SEED, &checksum, &fence, error,
			sizeof(error));
		if (ret) {
			fprintf(stderr, "%s: %s\n", error, strerror(-ret));
			binding.ops->queue_close(&queue);
			unload_hal_plugin(&binding);
			return 1;
		}
		printf("IREE Apollo Hexagon HAL: SG DMA stress ok queue=%u bytes=%u segments=%u checksum=0x%08x\n",
		       fence.queue_id,
		       APOLLO_HEXAGON_DMA_STRESS_BYTES,
		       APOLLO_HEXAGON_DMA_STRESS_SEGMENTS, checksum);
		printf("IREE Apollo Hexagon HAL: async fence signaled queue=%u fence=%u status=0x%08x\n",
		       fence.queue_id, fence.fence_seq, fence.status);
	}

	if (stress_only) {
		binding.ops->queue_close(&queue);
		unload_hal_plugin(&binding);
		return 0;
	}

	memset(&cmd, 0, sizeof(cmd));
	for (i = 0; i < APOLLO_HEXAGON_CNN_INPUT_WORDS; i++)
		cmd.input[i] = (uint32_t)i + 1;

	memset(&fence, 0, sizeof(fence));
	binding.ops->queue_select(&queue, 1);
	ret = binding.ops->queue_submit_cnn(&queue, &cmd, &fence, error,
					    sizeof(error));
	if (ret) {
		fprintf(stderr, "%s: %s\n", error, strerror(-ret));
		binding.ops->queue_close(&queue);
		unload_hal_plugin(&binding);
		return 1;
	}
	binding.ops->queue_close(&queue);
	unload_hal_plugin(&binding);

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
