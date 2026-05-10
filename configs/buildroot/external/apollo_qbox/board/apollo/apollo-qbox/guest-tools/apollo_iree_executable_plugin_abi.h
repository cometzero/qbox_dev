/* SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception */
#ifndef APOLLO_IREE_EXECUTABLE_PLUGIN_ABI_H
#define APOLLO_IREE_EXECUTABLE_PLUGIN_ABI_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define IREE_HAL_EXECUTABLE_PLUGIN_VERSION_0_1 0x00000001u
#define IREE_HAL_EXECUTABLE_PLUGIN_VERSION_LATEST \
	IREE_HAL_EXECUTABLE_PLUGIN_VERSION_0_1
#define IREE_HAL_EXECUTABLE_PLUGIN_FEATURE_STANDALONE (1u << 0)
#define IREE_HAL_EXECUTABLE_PLUGIN_RESOLUTION_MISSING_OPTIONAL (1u << 0)
#define IREE_HAL_EXECUTABLE_PLUGIN_EXPORT_NAME \
	"iree_hal_executable_plugin_query"

#if defined(_WIN32) || defined(__CYGWIN__)
#define IREE_HAL_EXECUTABLE_PLUGIN_EXPORT __declspec(dllexport)
#else
#define IREE_HAL_EXECUTABLE_PLUGIN_EXPORT __attribute__((visibility("default")))
#endif

typedef uint32_t iree_hal_executable_plugin_version_t;
typedef uint32_t iree_hal_executable_plugin_features_t;
typedef uint32_t iree_hal_executable_plugin_resolution_t;
typedef struct iree_status_handle_t *iree_hal_executable_plugin_status_t;

enum {
	IREE_HAL_EXECUTABLE_PLUGIN_STATUS_OK = 0,
	IREE_HAL_EXECUTABLE_PLUGIN_STATUS_NOT_FOUND = 5,
};

typedef struct iree_hal_executable_plugin_header_t {
	iree_hal_executable_plugin_version_t version;
	const char *name;
	const char *description;
	iree_hal_executable_plugin_features_t features;
	int32_t sanitizer;
	uint64_t reserved[8];
} iree_hal_executable_plugin_header_t;

typedef struct iree_hal_executable_plugin_string_view_t {
	const char *data;
	size_t size;
} iree_hal_executable_plugin_string_view_t;

typedef struct iree_hal_executable_plugin_string_pair_t {
	iree_hal_executable_plugin_string_view_t key;
	iree_hal_executable_plugin_string_view_t value;
} iree_hal_executable_plugin_string_pair_t;

typedef struct iree_hal_executable_plugin_allocator_t {
	void *self;
	iree_hal_executable_plugin_status_t (*ctl)(void *self, int command,
						     const void *params,
						     void **inout_ptr);
} iree_hal_executable_plugin_allocator_t;

typedef struct iree_hal_executable_plugin_environment_v0_t {
	iree_hal_executable_plugin_allocator_t host_allocator;
} iree_hal_executable_plugin_environment_v0_t;

typedef struct iree_hal_executable_plugin_resolve_params_v0_t {
	size_t count;
	const char *const *symbol_names;
	void **out_fn_ptrs;
	void **out_fn_contexts;
} iree_hal_executable_plugin_resolve_params_v0_t;

typedef iree_hal_executable_plugin_status_t (*iree_hal_executable_plugin_resolve_fn_v0_t)(
	void *self, const iree_hal_executable_plugin_resolve_params_v0_t *params,
	iree_hal_executable_plugin_resolution_t *out_resolution);

typedef struct iree_hal_executable_plugin_v0_t {
	const iree_hal_executable_plugin_header_t *header;
	iree_hal_executable_plugin_status_t (*load)(
		const iree_hal_executable_plugin_environment_v0_t *environment,
		size_t param_count,
		const iree_hal_executable_plugin_string_pair_t *params,
		void **out_self);
	void (*unload)(void *self);
	iree_hal_executable_plugin_resolve_fn_v0_t resolve;
} iree_hal_executable_plugin_v0_t;

static inline iree_hal_executable_plugin_status_t
apollo_iree_plugin_status_from_code(uint32_t code)
{
	return (iree_hal_executable_plugin_status_t)(uintptr_t)code;
}

static inline bool apollo_iree_plugin_symbol_optional(const char *symbol)
{
	return symbol && symbol[0] == '?';
}

#endif /* APOLLO_IREE_EXECUTABLE_PLUGIN_ABI_H */
