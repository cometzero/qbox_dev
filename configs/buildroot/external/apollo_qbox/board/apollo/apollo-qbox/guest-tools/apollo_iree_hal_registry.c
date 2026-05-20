// SPDX-License-Identifier: MIT
#include "apollo_iree_hal_registry.h"

#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

static void set_error(char *error, size_t error_len, const char *fmt,
		      const char *arg)
{
	if (!error || error_len == 0)
		return;
	if (arg)
		snprintf(error, error_len, fmt, arg);
	else
		snprintf(error, error_len, "%s", fmt);
}

static int registry_queue_open(struct apollo_hexagon_queue *queue,
			       const char *device, char *error, size_t error_len)
{
	return apollo_hexagon_queue_open(queue, device, error, error_len);
}

static void registry_queue_close(struct apollo_hexagon_queue *queue)
{
	apollo_hexagon_queue_close(queue);
}

static void registry_queue_select(struct apollo_hexagon_queue *queue,
				  uint32_t queue_id)
{
	apollo_hexagon_queue_select(queue, queue_id);
}

static int registry_queue_submit_cnn(struct apollo_hexagon_queue *queue,
				     struct apollo_hexagon_command_buffer *cmd,
				     struct apollo_hexagon_fence *fence,
				     char *error, size_t error_len)
{
	return apollo_hexagon_queue_submit_cnn(queue, cmd, fence, error,
					     error_len);
}

static int registry_queue_submit_dma_stress(struct apollo_hexagon_queue *queue,
					    uint32_t bytes, uint32_t seed,
					    uint32_t *checksum,
					    struct apollo_hexagon_fence *fence,
					    char *error, size_t error_len)
{
	return apollo_hexagon_queue_submit_dma_stress(queue, bytes, seed,
						    checksum, fence, error,
						    error_len);
}

static int registry_queue_submit_vadd(struct apollo_hexagon_queue *queue,
				      struct apollo_hexagon_vadd_command_buffer *cmd,
				      struct apollo_hexagon_fence *fence,
				      char *error, size_t error_len)
{
	return apollo_hexagon_queue_submit_vadd(queue, cmd, fence, error,
					       error_len);
}

static int registry_queue_submit_apko(
	struct apollo_hexagon_queue *queue,
	const struct apollo_hexagon_executable *exe, const void *input,
	size_t input_bytes, void *output, size_t output_bytes,
	struct apollo_hexagon_fence *fence, char *error, size_t error_len)
{
	return apollo_hexagon_queue_submit_apko(queue, exe, input, input_bytes,
					       output, output_bytes, fence,
					       error, error_len);
}

static const struct apollo_iree_hexagon_plugin_v1 apollo_registry_ops = {
	.api_version = APOLLO_IREE_HEXAGON_PLUGIN_API_VERSION,
	.name = "apollo-hexagon-hal-registry",
	.description = "Apollo QBox upstream-style registered HAL device",
	.queue_open = registry_queue_open,
	.queue_close = registry_queue_close,
	.queue_select = registry_queue_select,
	.queue_submit_cnn = registry_queue_submit_cnn,
	.queue_submit_vadd = registry_queue_submit_vadd,
	.queue_submit_apko = registry_queue_submit_apko,
	.queue_submit_dma_stress = registry_queue_submit_dma_stress,
};

static void *apollo_dynamic_plugin_handle;
static struct apollo_iree_hal_device apollo_dynamic_device = {
	.name = "apollo-hexagon",
	.description = "Apollo QBox dynamically registered Hexagon HAL device",
	.plugin_path = NULL,
	.ops = &apollo_registry_ops,
};

static int is_cpu_fallback_device(const char *device_name)
{
	return strcmp(device_name, "local") == 0 ||
	       strcmp(device_name, "local-task") == 0 ||
	       strcmp(device_name, "local-sync") == 0 ||
	       strcmp(device_name, "llvm-cpu") == 0;
}

static int apollo_iree_hal_registry_load_plugin(const char *plugin_path,
						char *error,
						size_t error_len)
{
	apollo_iree_hexagon_plugin_query_fn_t query;
	const struct apollo_iree_hexagon_plugin_v1 *ops;

	if (!plugin_path || !plugin_path[0]) {
		set_error(error, error_len,
			  "missing Apollo HAL plugin path for dynamic registry",
			  NULL);
		return -EINVAL;
	}

	if (apollo_dynamic_plugin_handle) {
		dlclose(apollo_dynamic_plugin_handle);
		apollo_dynamic_plugin_handle = NULL;
		apollo_dynamic_device.ops = &apollo_registry_ops;
		apollo_dynamic_device.plugin_path = NULL;
	}

	apollo_dynamic_plugin_handle = dlopen(plugin_path, RTLD_NOW | RTLD_LOCAL);
	if (!apollo_dynamic_plugin_handle) {
		set_error(error, error_len,
			  "failed to dlopen Apollo HAL plugin %s", plugin_path);
		return -EINVAL;
	}

	query = (apollo_iree_hexagon_plugin_query_fn_t)dlsym(
		apollo_dynamic_plugin_handle,
		APOLLO_IREE_HEXAGON_PLUGIN_EXPORT_NAME);
	if (!query) {
		set_error(error, error_len,
			  "Apollo HAL plugin missing query export %s",
			  APOLLO_IREE_HEXAGON_PLUGIN_EXPORT_NAME);
		dlclose(apollo_dynamic_plugin_handle);
		apollo_dynamic_plugin_handle = NULL;
		return -EINVAL;
	}

	ops = query(APOLLO_IREE_HEXAGON_PLUGIN_API_VERSION);
	if (!ops || ops->api_version != APOLLO_IREE_HEXAGON_PLUGIN_API_VERSION ||
	    !ops->queue_open || !ops->queue_close || !ops->queue_select ||
	    !ops->queue_submit_cnn || !ops->queue_submit_vadd ||
	    !ops->queue_submit_apko ||
	    !ops->queue_submit_dma_stress) {
		set_error(error, error_len,
			  "Apollo HAL plugin has incompatible ABI", NULL);
		dlclose(apollo_dynamic_plugin_handle);
		apollo_dynamic_plugin_handle = NULL;
		return -EINVAL;
	}

	apollo_dynamic_device.ops = ops;
	apollo_dynamic_device.plugin_path = plugin_path;
	return 0;
}

const struct apollo_iree_hal_device *apollo_iree_hal_registry_lookup(
	const char *device_name, const char *plugin_path, char *error,
	size_t error_len)
{
	int ret;

	if (!device_name || !device_name[0]) {
		set_error(error, error_len,
			  "missing --device=apollo-hexagon for Apollo HAL registry",
			  NULL);
		return NULL;
	}
	if (is_cpu_fallback_device(device_name)) {
		set_error(error, error_len,
			  "CPU fallback device is disabled for Apollo proof: %s",
			  device_name);
		return NULL;
	}
	if (strcmp(apollo_dynamic_device.name, device_name) == 0) {
		ret = apollo_iree_hal_registry_load_plugin(plugin_path, error,
							   error_len);
		if (ret)
			return NULL;
		return &apollo_dynamic_device;
	}
	set_error(error, error_len, "unknown IREE HAL device: %s", device_name);
	return NULL;
}

int apollo_iree_hal_registry_open_queue(
	const struct apollo_iree_hal_device *device,
	struct apollo_hexagon_queue *queue, const char *device_path,
	char *error, size_t error_len)
{
	if (!device || !device->ops || !device->ops->queue_open) {
		set_error(error, error_len,
			  "Apollo HAL registry entry has no queue_open", NULL);
		return -EINVAL;
	}
	return device->ops->queue_open(queue, device_path, error, error_len);
}
