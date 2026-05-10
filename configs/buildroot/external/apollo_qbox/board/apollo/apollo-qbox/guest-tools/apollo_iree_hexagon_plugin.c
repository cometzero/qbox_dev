/* SPDX-License-Identifier: MIT */
#include "apollo_iree_hexagon_plugin.h"
#include "apollo_iree_executable_plugin_abi.h"

#include <stddef.h>

static const struct apollo_iree_hexagon_plugin_v1 apollo_plugin = {
	.api_version = APOLLO_IREE_HEXAGON_PLUGIN_API_VERSION,
	.name = "apollo-hexagon-hal",
	.description = "Apollo QBox Hexagon userspace HAL plugin",
	.queue_open = apollo_hexagon_queue_open,
	.queue_close = apollo_hexagon_queue_close,
	.queue_select = apollo_hexagon_queue_select,
	.queue_submit_cnn = apollo_hexagon_queue_submit_cnn,
	.queue_submit_dma_stress = apollo_hexagon_queue_submit_dma_stress,
};

__attribute__((visibility("default")))
const struct apollo_iree_hexagon_plugin_v1 *apollo_iree_hexagon_plugin_query(
	uint32_t max_version)
{
	if (max_version < APOLLO_IREE_HEXAGON_PLUGIN_API_VERSION)
		return NULL;
	return &apollo_plugin;
}

static iree_hal_executable_plugin_status_t apollo_iree_load(
	const iree_hal_executable_plugin_environment_v0_t *environment,
	size_t param_count,
	const iree_hal_executable_plugin_string_pair_t *params,
	void **out_self)
{
	(void)environment;
	(void)param_count;
	(void)params;
	*out_self = NULL;
	return apollo_iree_plugin_status_from_code(
		IREE_HAL_EXECUTABLE_PLUGIN_STATUS_OK);
}

static void apollo_iree_unload(void *self)
{
	(void)self;
}

static iree_hal_executable_plugin_status_t apollo_iree_resolve(
	void *self, const iree_hal_executable_plugin_resolve_params_v0_t *params,
	iree_hal_executable_plugin_resolution_t *out_resolution)
{
	size_t i;
	int missing_required = 0;

	(void)self;
	*out_resolution = 0;
	for (i = 0; i < params->count; i++) {
		const char *symbol = params->symbol_names[i];

		if (params->out_fn_ptrs[i])
			continue;
		if (apollo_iree_plugin_symbol_optional(symbol)) {
			params->out_fn_ptrs[i] = NULL;
			if (params->out_fn_contexts)
				params->out_fn_contexts[i] = NULL;
			*out_resolution |=
				IREE_HAL_EXECUTABLE_PLUGIN_RESOLUTION_MISSING_OPTIONAL;
			continue;
		}
		missing_required = 1;
	}

	return apollo_iree_plugin_status_from_code(missing_required ?
		IREE_HAL_EXECUTABLE_PLUGIN_STATUS_NOT_FOUND :
		IREE_HAL_EXECUTABLE_PLUGIN_STATUS_OK);
}

static const iree_hal_executable_plugin_header_t apollo_iree_header = {
	.version = IREE_HAL_EXECUTABLE_PLUGIN_VERSION_LATEST,
	.name = "apollo-hexagon-executable-plugin",
	.description = "IREE local executable plugin shim for Apollo QBox Hexagon",
	.features = IREE_HAL_EXECUTABLE_PLUGIN_FEATURE_STANDALONE,
	.sanitizer = 0,
	.reserved = {0},
};

static const iree_hal_executable_plugin_v0_t apollo_iree_plugin = {
	.header = &apollo_iree_header,
	.load = apollo_iree_load,
	.unload = apollo_iree_unload,
	.resolve = apollo_iree_resolve,
};

IREE_HAL_EXECUTABLE_PLUGIN_EXPORT
const iree_hal_executable_plugin_header_t **iree_hal_executable_plugin_query(
	iree_hal_executable_plugin_version_t max_version, void *reserved)
{
	(void)reserved;
	if (max_version < IREE_HAL_EXECUTABLE_PLUGIN_VERSION_0_1)
		return NULL;
	return (const iree_hal_executable_plugin_header_t **)&apollo_iree_plugin;
}
