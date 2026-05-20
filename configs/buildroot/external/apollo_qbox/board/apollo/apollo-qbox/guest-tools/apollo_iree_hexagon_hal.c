// SPDX-License-Identifier: MIT
#include "apollo_iree_hexagon_hal.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#define APOLLO_HEXAGON_ACCEL_SCAN_MAX 256
#define APOLLO_HEXAGON_VMFB_APKO_FOOTER_MAGIC 0x4f4b4156u
#define APOLLO_HEXAGON_VMFB_APKO_FOOTER_VERSION 0u
#define APOLLO_HEXAGON_VMFB_APKO_FOOTER_WORDS 8u
#define APOLLO_HEXAGON_VMFB_APKO_FOOTER_BYTES \
	(APOLLO_HEXAGON_VMFB_APKO_FOOTER_WORDS * sizeof(uint32_t))

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

static int copy_string(char *dst, size_t dst_len, const char *src)
{
	int ret;

	ret = snprintf(dst, dst_len, "%s", src);
	return ret >= 0 && (size_t)ret < dst_len ? 0 : -ENAMETOOLONG;
}

static int join_relative(char *dst, size_t dst_len, const char *base,
			 const char *name)
{
	const char *slash;
	int ret;

	if (!name || !name[0])
		return -EINVAL;
	if (name[0] == '/')
		return copy_string(dst, dst_len, name);
	if (!base || !base[0])
		return copy_string(dst, dst_len, name);

	slash = strrchr(base, '/');
	if (!slash)
		return copy_string(dst, dst_len, name);

	ret = snprintf(dst, dst_len, "%.*s/%s", (int)(slash - base), base,
		       name);
	return ret >= 0 && (size_t)ret < dst_len ? 0 : -ENAMETOOLONG;
}

static void trim_line(char *line)
{
	size_t len = strlen(line);

	while (len > 0 && (line[len - 1] == '\n' || line[len - 1] == '\r' ||
			 line[len - 1] == ' ' || line[len - 1] == '\t')) {
		line[len - 1] = '\0';
		len--;
	}
}

static int parse_u32(const char *value, uint32_t *out)
{
	char *end = NULL;
	unsigned long parsed;

	errno = 0;
	parsed = strtoul(value, &end, 0);
	if (errno || !end || *end || parsed > UINT32_MAX)
		return -EINVAL;
	*out = (uint32_t)parsed;
	return 0;
}

static uint32_t entry_kind_from_name(const char *name)
{
	if (!name)
		return 0;
	if (strcmp(name, "tiny_cnn_graph") == 0 ||
	    strcmp(name, "cnn") == 0)
		return APOLLO_HEXAGON_EXEC_KIND_CNN;
	if (strcmp(name, "vector_add_graph") == 0 ||
	    strcmp(name, "vadd") == 0)
		return APOLLO_HEXAGON_EXEC_KIND_VADD;
	if (strcmp(name, "mnist_graph") == 0 ||
	    strcmp(name, "mnist") == 0)
		return APOLLO_HEXAGON_EXEC_KIND_MNIST;
	return 0;
}

static int set_entry_defaults(struct apollo_hexagon_executable *exe,
			      uint32_t entry_kind)
{
	switch (entry_kind) {
	case APOLLO_HEXAGON_EXEC_KIND_CNN:
		if (copy_string(exe->entry_point, sizeof(exe->entry_point),
				"tiny_cnn_graph") ||
		    copy_string(exe->expected_output,
				sizeof(exe->expected_output),
				"1x1x2x2xf32=[[[54 63][90 99]]]"))
			return -ENAMETOOLONG;
		exe->entry_kind = entry_kind;
		if (!exe->input_bytes)
			exe->input_bytes =
				APOLLO_HEXAGON_CNN_INPUT_WORDS *
				sizeof(uint32_t);
		if (!exe->output_bytes)
			exe->output_bytes =
				APOLLO_HEXAGON_CNN_OUTPUT_WORDS *
				sizeof(uint32_t);
		return 0;
	case APOLLO_HEXAGON_EXEC_KIND_VADD:
		if (copy_string(exe->entry_point, sizeof(exe->entry_point),
				"vector_add_graph") ||
		    copy_string(exe->expected_output,
				sizeof(exe->expected_output),
				"4xf32=11 22 33 44"))
			return -ENAMETOOLONG;
		exe->entry_kind = entry_kind;
		if (!exe->input_bytes)
			exe->input_bytes =
				APOLLO_HEXAGON_VADD_INPUT_WORDS *
				sizeof(uint32_t);
		if (!exe->output_bytes)
			exe->output_bytes =
				APOLLO_HEXAGON_VADD_OUTPUT_WORDS *
				sizeof(uint32_t);
		return 0;
	case APOLLO_HEXAGON_EXEC_KIND_MNIST:
		if (copy_string(exe->entry_point, sizeof(exe->entry_point),
				"mnist_graph") ||
		    copy_string(exe->expected_output,
				sizeof(exe->expected_output),
				"1x10xf32=[0 1 2 3 4 5 6 7 8 9]"))
			return -ENAMETOOLONG;
		exe->entry_kind = entry_kind;
		if (!exe->input_bytes)
			exe->input_bytes =
				APOLLO_HEXAGON_MNIST_INPUT_WORDS *
				sizeof(uint32_t);
		if (!exe->output_bytes)
			exe->output_bytes =
				APOLLO_HEXAGON_MNIST_OUTPUT_WORDS *
				sizeof(uint32_t);
		return 0;
	default:
		return -EINVAL;
	}
}

static int infer_entry_defaults_from_module(
	struct apollo_hexagon_executable *exe, const char *module_path)
{
	const char *name;

	if (!module_path)
		return 0;
	name = strrchr(module_path, '/');
	name = name ? name + 1 : module_path;
	if (strstr(name, "vector_add"))
		return set_entry_defaults(exe, APOLLO_HEXAGON_EXEC_KIND_VADD);
	if (strstr(name, "mnist"))
		return set_entry_defaults(exe, APOLLO_HEXAGON_EXEC_KIND_MNIST);
	if (strstr(name, "tiny_cnn") || strstr(name, "cnn"))
		return set_entry_defaults(exe, APOLLO_HEXAGON_EXEC_KIND_CNN);
	return 0;
}

static int validate_query_caps(const struct drm_apollo_hexagon_query_caps *caps)
{
	if (caps->generic_abi_version != APOLLO_HEXAGON_GENERIC_ABI_VERSION)
		return -EINVAL;
	if (!(caps->supported_executable_formats &
	      APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0_BIT))
		return -EINVAL;
	if (caps->fence_model != APOLLO_HEXAGON_FENCE_MODEL_ASYNC_IRQ_POLL)
		return -EINVAL;
	if (caps->fault_record_size != sizeof(struct drm_apollo_hexagon_fault))
		return -EINVAL;
	return 0;
}

static int read_whole_file(const char *path, void **out_data,
			   size_t *out_size, char *error, size_t error_len)
{
	struct stat st;
	unsigned char *data;
	FILE *fp;
	size_t got;

	if (stat(path, &st)) {
		set_error(error, error_len, "failed to stat APKO %s", path);
		return -errno;
	}
	if (st.st_size <= 0 || (uint64_t)st.st_size > UINT32_MAX) {
		set_error(error, error_len, "invalid APKO size for %s", path);
		return -EINVAL;
	}

	data = malloc((size_t)st.st_size);
	if (!data) {
		set_error(error, error_len, "failed to allocate APKO buffer",
			  NULL);
		return -ENOMEM;
	}

	fp = fopen(path, "rb");
	if (!fp) {
		int ret = -errno;

		free(data);
		set_error(error, error_len, "failed to open APKO %s", path);
		return ret;
	}

	got = fread(data, 1, (size_t)st.st_size, fp);
	if (got != (size_t)st.st_size) {
		int ret = ferror(fp) && errno ? -errno : -EIO;

		fclose(fp);
		free(data);
		set_error(error, error_len, "failed to read APKO %s", path);
		return ret;
	}
	fclose(fp);

	*out_data = data;
	*out_size = (size_t)st.st_size;
	return 0;
}

static int read_apko_payload_program(const void *data, size_t size,
				     uint32_t entry_kind,
				     uint32_t *payload_opcode,
				     uint32_t *code_words,
				     uint32_t *entry_word)
{
	struct drm_apollo_hexagon_apko_header header;
	uint32_t descriptor[APOLLO_HEXAGON_APKO_PAYLOAD_DESCRIPTOR_WORDS];
	uint32_t code_desc[APOLLO_HEXAGON_APKO_CODE_DESCRIPTOR_WORDS];
	const unsigned char *bytes = data;
	uint32_t code_entry_kind;
	size_t code_desc_offset;
	size_t code_offset;

	if (!data || size < sizeof(header))
		return -EINVAL;

	memcpy(&header, bytes, sizeof(header));
	if (header.header_bytes < sizeof(header) ||
	    header.header_bytes > size ||
	    header.header_bytes % sizeof(uint32_t))
		return -EINVAL;
	if (size - header.header_bytes < sizeof(descriptor))
		return -ENODATA;

	memcpy(descriptor, bytes + header.header_bytes, sizeof(descriptor));
	if (descriptor[0] != APOLLO_HEXAGON_APKO_PAYLOAD_MAGIC ||
	    descriptor[1] != APOLLO_HEXAGON_APKO_PAYLOAD_VERSION ||
	    descriptor[3] != APOLLO_HEXAGON_APKO_PAYLOAD_DESCRIPTOR_WORDS)
		return -EINVAL;
	if (descriptor[2] != entry_kind)
		return -EINVAL;

	code_desc_offset = header.header_bytes + sizeof(descriptor);
	if (size - code_desc_offset < sizeof(code_desc))
		return -EINVAL;
	memcpy(code_desc, bytes + code_desc_offset, sizeof(code_desc));
	if (code_desc[0] != APOLLO_HEXAGON_APKO_CODE_MAGIC ||
	    code_desc[1] != APOLLO_HEXAGON_APKO_CODE_VERSION ||
	    code_desc[3] != APOLLO_HEXAGON_APKO_CODE_DESCRIPTOR_WORDS ||
	    code_desc[2] == 0)
		return -EINVAL;

	code_offset = code_desc_offset + sizeof(code_desc);
	if ((size_t)code_desc[2] >
	    (size - code_offset) / sizeof(uint32_t))
		return -EINVAL;
	*payload_opcode = descriptor[2];
	*code_words = code_desc[2];
	memcpy(entry_word, bytes + code_offset, sizeof(*entry_word));
	if ((*entry_word & APOLLO_HEXAGON_APKO_CODE_OP_MASK) !=
	    APOLLO_HEXAGON_APKO_CODE_OP_MODEL_DISPATCH)
		return -EINVAL;
	code_entry_kind = *entry_word &
			  APOLLO_HEXAGON_APKO_CODE_MODEL_MASK;
	if (code_entry_kind != *payload_opcode)
		return -EINVAL;
	return 0;
}

static int load_embedded_apko_from_module(
	const char *module_path, struct apollo_hexagon_executable *exe,
	char *error, size_t error_len)
{
	uint32_t footer[APOLLO_HEXAGON_VMFB_APKO_FOOTER_WORDS];
	uint32_t header[12];
	unsigned char *data;
	struct stat st;
	FILE *fp;
	long apko_offset;
	size_t got;

	if (stat(module_path, &st)) {
		set_error(error, error_len, "failed to stat module %s",
			  module_path);
		return -errno;
	}
	if ((uint64_t)st.st_size < APOLLO_HEXAGON_VMFB_APKO_FOOTER_BYTES)
		return 0;

	fp = fopen(module_path, "rb");
	if (!fp) {
		set_error(error, error_len, "failed to open module %s",
			  module_path);
		return -errno;
	}
	if (fseek(fp, -(long)APOLLO_HEXAGON_VMFB_APKO_FOOTER_BYTES,
		  SEEK_END)) {
		int ret = -errno;

		fclose(fp);
		set_error(error, error_len, "failed to seek module %s",
			  module_path);
		return ret;
	}
	got = fread(footer, 1, sizeof(footer), fp);
	if (got != sizeof(footer)) {
		int ret = ferror(fp) && errno ? -errno : -EIO;

		fclose(fp);
		set_error(error, error_len, "failed to read module footer %s",
			  module_path);
		return ret;
	}
	if (footer[0] != APOLLO_HEXAGON_VMFB_APKO_FOOTER_MAGIC) {
		fclose(fp);
		return 0;
	}
	if (footer[1] != APOLLO_HEXAGON_VMFB_APKO_FOOTER_VERSION ||
	    footer[2] != APOLLO_HEXAGON_VMFB_APKO_FOOTER_BYTES ||
	    footer[3] < sizeof(header) || footer[7] ||
	    (uint64_t)footer[3] >
		    (uint64_t)st.st_size -
		    APOLLO_HEXAGON_VMFB_APKO_FOOTER_BYTES) {
		fclose(fp);
		set_error(error, error_len,
			  "invalid embedded APKO footer in module %s",
			  module_path);
		return -EINVAL;
	}

	apko_offset = st.st_size - APOLLO_HEXAGON_VMFB_APKO_FOOTER_BYTES -
		      footer[3];
	if (fseek(fp, apko_offset, SEEK_SET)) {
		int ret = -errno;

		fclose(fp);
		set_error(error, error_len, "failed to seek embedded APKO %s",
			  module_path);
		return ret;
	}
	data = malloc(footer[3]);
	if (!data) {
		fclose(fp);
		set_error(error, error_len,
			  "failed to allocate embedded APKO buffer", NULL);
		return -ENOMEM;
	}
	got = fread(data, 1, footer[3], fp);
	fclose(fp);
	if (got != footer[3]) {
		free(data);
		set_error(error, error_len, "failed to read embedded APKO %s",
			  module_path);
		return -EIO;
	}

	memcpy(header, data, sizeof(header));
	if (header[0] != APOLLO_HEXAGON_APKO_MAGIC ||
	    header[1] != sizeof(header) ||
	    header[2] != APOLLO_HEXAGON_APKO_ABI_VERSION ||
	    header[3] != APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0 ||
	    header[4] != footer[4] || header[5] != footer[5] ||
	    header[6] != footer[6]) {
		free(data);
		set_error(error, error_len,
			  "embedded APKO header/footer mismatch in module %s",
			  module_path);
		return -EINVAL;
	}

	if (set_entry_defaults(exe, footer[4])) {
		free(data);
		set_error(error, error_len,
			  "unsupported embedded APKO entry kind in module %s",
			  module_path);
		return -EINVAL;
	}
	exe->executable_format = APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0;
	exe->apko_abi_version = APOLLO_HEXAGON_APKO_ABI_VERSION;
	exe->input_bytes = footer[5];
	exe->output_bytes = footer[6];
	exe->apko_data = data;
	exe->apko_data_size = footer[3];
	exe->apko_size = footer[3];
	exe->apko_embedded = 1;
	if (snprintf(exe->apko_path, sizeof(exe->apko_path),
		     "embedded:%s", module_path) >=
	    (int)sizeof(exe->apko_path)) {
		free(data);
		exe->apko_data = NULL;
		exe->apko_data_size = 0;
		exe->apko_size = 0;
		exe->apko_embedded = 0;
		set_error(error, error_len,
			  "embedded APKO module path is too long", NULL);
		return -ENAMETOOLONG;
	}

	return 0;
}

struct apollo_hexagon_mapped_bo {
	uint32_t handle;
	uint64_t size;
	uint64_t mmap_offset;
	void *map;
};

struct apollo_hexagon_bound_bo {
	uint32_t handle;
	uint64_t iova;
};

static const char *apollo_hexagon_exec_kind_name(uint32_t entry_kind)
{
	switch (entry_kind) {
	case APOLLO_HEXAGON_EXEC_KIND_CNN:
		return "CNN";
	case APOLLO_HEXAGON_EXEC_KIND_VADD:
		return "VADD";
	case APOLLO_HEXAGON_EXEC_KIND_MNIST:
		return "MNIST";
	default:
		return "unknown";
	}
}

static int create_mapped_bo(int fd, struct apollo_hexagon_mapped_bo *bo,
			    size_t size, char *error, size_t error_len)
{
	struct drm_apollo_hexagon_bo_create create;

	memset(bo, 0, sizeof(*bo));
	bo->map = MAP_FAILED;
	memset(&create, 0, sizeof(create));
	create.size = sizeof(create);
	create.bo_size = size;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_CREATE, &create) < 0) {
		set_error(error, error_len,
			  "DRM_IOCTL_APOLLO_HEXAGON_BO_CREATE failed", NULL);
		return -errno;
	}

	bo->handle = create.handle;
	bo->size = create.bo_size;
	bo->mmap_offset = create.mmap_offset;
	bo->map = mmap(NULL, (size_t)bo->size, PROT_READ | PROT_WRITE,
		       MAP_SHARED, fd, (off_t)bo->mmap_offset);
	if (bo->map == MAP_FAILED) {
		struct drm_apollo_hexagon_bo_destroy destroy = {
			.handle = bo->handle,
		};
		int ret = -errno;

		ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_DESTROY, &destroy);
		memset(bo, 0, sizeof(*bo));
		bo->map = MAP_FAILED;
		set_error(error, error_len, "failed to mmap Apollo Hexagon BO",
			  NULL);
		return ret;
	}

	return 0;
}

static int destroy_mapped_bo(int fd, struct apollo_hexagon_mapped_bo *bo,
			     char *error, size_t error_len)
{
	struct drm_apollo_hexagon_bo_destroy destroy;
	int ret = 0;

	if (bo->map && bo->map != MAP_FAILED) {
		if (munmap(bo->map, (size_t)bo->size) < 0 && !ret) {
			ret = -errno;
			set_error(error, error_len,
				  "failed to munmap Apollo Hexagon BO", NULL);
		}
	}
	bo->map = MAP_FAILED;

	if (bo->handle) {
		memset(&destroy, 0, sizeof(destroy));
		destroy.handle = bo->handle;
		if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_DESTROY,
			  &destroy) < 0 && !ret) {
			ret = -errno;
			set_error(error, error_len,
				  "DRM_IOCTL_APOLLO_HEXAGON_BO_DESTROY failed",
				  NULL);
		}
	}
	memset(bo, 0, sizeof(*bo));
	bo->map = MAP_FAILED;
	return ret;
}

static int bind_bo(int fd, uint32_t context_handle,
		   const struct apollo_hexagon_mapped_bo *bo, uint32_t usage,
		   struct apollo_hexagon_bound_bo *bound, char *error,
		   size_t error_len)
{
	struct drm_apollo_hexagon_bo_bind bind;

	memset(bound, 0, sizeof(*bound));
	memset(&bind, 0, sizeof(bind));
	bind.size = sizeof(bind);
	bind.context_handle = context_handle;
	bind.bo_handle = bo->handle;
	bind.length = bo->size;
	bind.usage = usage;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_BIND, &bind) < 0) {
		set_error(error, error_len,
			  "DRM_IOCTL_APOLLO_HEXAGON_BO_BIND failed", NULL);
		return -errno;
	}

	bound->handle = bind.bind_handle;
	bound->iova = bind.iova;
	return 0;
}

static int unbind_bo(int fd, uint32_t context_handle,
		     struct apollo_hexagon_bound_bo *bound, char *error,
		     size_t error_len)
{
	struct drm_apollo_hexagon_bo_unbind unbind;

	if (!bound->handle)
		return 0;

	memset(&unbind, 0, sizeof(unbind));
	unbind.size = sizeof(unbind);
	unbind.context_handle = context_handle;
	unbind.bind_handle = bound->handle;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_UNBIND, &unbind) < 0) {
		set_error(error, error_len,
			  "DRM_IOCTL_APOLLO_HEXAGON_BO_UNBIND failed", NULL);
		return -errno;
	}
	memset(bound, 0, sizeof(*bound));
	return 0;
}

static int apollo_hexagon_queue_submit_apko_cmdq(
	struct apollo_hexagon_queue *queue, uint32_t executable_handle,
	uint32_t entry_kind, uint32_t payload_opcode, uint32_t code_words,
	uint32_t entry_word, const void *input, size_t input_bytes,
	void *output, size_t output_bytes,
	struct apollo_hexagon_fence *fence, char *error, size_t error_len)
{
	struct drm_apollo_hexagon_context_create context;
	struct drm_apollo_hexagon_context_destroy destroy_context;
	struct drm_apollo_hexagon_cmd_submit submit;
	struct apollo_hexagon_mapped_bo command_bo;
	struct apollo_hexagon_mapped_bo input_bo;
	struct apollo_hexagon_mapped_bo output_bo;
	struct apollo_hexagon_bound_bo input_bind;
	struct apollo_hexagon_bound_bo output_bind;
	uint32_t *packet;
	const uint32_t exec_slot = 1;
	uint32_t context_handle = 0;
	int ret;
	int cleanup_ret;

	memset(&command_bo, 0, sizeof(command_bo));
	memset(&input_bo, 0, sizeof(input_bo));
	memset(&output_bo, 0, sizeof(output_bo));
	command_bo.map = MAP_FAILED;
	input_bo.map = MAP_FAILED;
	output_bo.map = MAP_FAILED;
	memset(&input_bind, 0, sizeof(input_bind));
	memset(&output_bind, 0, sizeof(output_bind));

	memset(&context, 0, sizeof(context));
	context.size = sizeof(context);
	context.generic_abi_version = APOLLO_HEXAGON_GENERIC_ABI_VERSION;
	if (ioctl(queue->fd, DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_CREATE,
		  &context) < 0) {
		set_error(error, error_len,
			  "DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_CREATE failed", NULL);
		return -errno;
	}
	context_handle = context.handle;

	ret = create_mapped_bo(queue->fd, &input_bo, input_bytes, error,
			       error_len);
	if (ret)
		goto out_context;
	ret = create_mapped_bo(queue->fd, &output_bo, output_bytes, error,
			       error_len);
	if (ret)
		goto out_input_bo;
	ret = create_mapped_bo(queue->fd, &command_bo,
			       APOLLO_HEXAGON_CMDQ_SUBMIT_MAX_BYTES, error,
			       error_len);
	if (ret)
		goto out_output_bo;

	memcpy(input_bo.map, input, input_bytes);
	memset(output_bo.map, 0, output_bytes);
	ret = bind_bo(queue->fd, context_handle, &input_bo,
		      APOLLO_HEXAGON_BO_BIND_USAGE_READ, &input_bind, error,
		      error_len);
	if (ret)
		goto out_command_bo;
	ret = bind_bo(queue->fd, context_handle, &output_bo,
		      APOLLO_HEXAGON_BO_BIND_USAGE_WRITE, &output_bind, error,
		      error_len);
	if (ret)
		goto out_input_unbind;

	packet = command_bo.map;
	memset(packet, 0, APOLLO_HEXAGON_CMDQ_SUBMIT_MAX_BYTES);
	packet[0] = APOLLO_HEXAGON_CMDQ_OPCODE_LOAD_EXECUTABLE;
	packet[1] = exec_slot;
	packet[2] = APOLLO_HEXAGON_APKO_MAGIC;
	packet[3] = APOLLO_HEXAGON_APKO_ABI_VERSION;
	packet[4] = APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0;
	packet[5] = entry_kind;
	packet[6] = (uint32_t)input_bytes;
	packet[7] = (uint32_t)output_bytes;
	packet += APOLLO_HEXAGON_CMDQ_PACKET_WORDS;
	packet[0] = APOLLO_HEXAGON_CMDQ_OPCODE_LOAD_PAYLOAD;
	packet[1] = exec_slot;
	packet[2] = APOLLO_HEXAGON_APKO_PAYLOAD_MAGIC;
	packet[3] = APOLLO_HEXAGON_APKO_PAYLOAD_VERSION;
	packet[4] = payload_opcode;
	packet[5] = APOLLO_HEXAGON_APKO_PAYLOAD_DESCRIPTOR_WORDS;
	packet[6] = code_words;
	packet[7] = entry_word;
	packet += APOLLO_HEXAGON_CMDQ_PACKET_WORDS;
	packet[0] = APOLLO_HEXAGON_CMDQ_OPCODE_DISPATCH;
	packet[1] = APOLLO_HEXAGON_CMDQ_DISPATCH_EXEC_SLOT_FLAG | exec_slot;
	packet[2] = (uint32_t)input_bind.iova;
	packet[3] = (uint32_t)(input_bind.iova >> 32);
	packet[4] = (uint32_t)output_bind.iova;
	packet[5] = (uint32_t)(output_bind.iova >> 32);
	packet[6] = (uint32_t)input_bytes;
	packet[7] = (uint32_t)output_bytes;

	memset(&submit, 0, sizeof(submit));
	submit.size = sizeof(submit);
	submit.context_handle = context_handle;
	submit.command_bo_handle = command_bo.handle;
	submit.command_size = APOLLO_HEXAGON_CMDQ_SUBMIT_MAX_BYTES;
	submit.queue_id = queue->queue_id;
	if (ioctl(queue->fd, DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT, &submit) < 0) {
		ret = -errno;
		set_error(error, error_len,
			  "DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT failed", NULL);
		goto out_output_unbind;
	}

	memcpy(output, output_bo.map, output_bytes);
	if (entry_kind == APOLLO_HEXAGON_EXEC_KIND_VADD)
		fence->status = APOLLO_HEXAGON_HAL_STATUS_VADD_OK;
	else if (entry_kind == APOLLO_HEXAGON_EXEC_KIND_MNIST)
		fence->status = APOLLO_HEXAGON_HAL_STATUS_MNIST_OK;
	else
		fence->status = APOLLO_HEXAGON_HAL_STATUS_OK;
	fence->signaled = 1;
	fence->queue_id = submit.queue_id;
	fence->fence_seq = submit.fence_seq;
	printf("IREE Apollo Hexagon HAL: APKO CMD_SUBMIT %s ok executable=%u exec_slot=%u payload_opcode=%u code_words=%u code_entry=%u ctx=%u cmd_bo=%u input_bind=%u output_bind=%u queue=%u fence=%u status=0x%08x result=0x%08x\n",
	       apollo_hexagon_exec_kind_name(entry_kind), executable_handle,
	       exec_slot, payload_opcode, code_words, entry_word, context_handle,
	       command_bo.handle, input_bind.handle, output_bind.handle,
	       submit.queue_id, submit.fence_seq, submit.status, submit.result);
	ret = 0;

out_output_unbind:
	cleanup_ret = unbind_bo(queue->fd, context_handle, &output_bind, error,
				error_len);
	if (cleanup_ret && !ret)
		ret = cleanup_ret;
out_input_unbind:
	cleanup_ret = unbind_bo(queue->fd, context_handle, &input_bind, error,
				error_len);
	if (cleanup_ret && !ret)
		ret = cleanup_ret;
out_command_bo:
	cleanup_ret = destroy_mapped_bo(queue->fd, &command_bo, error, error_len);
	if (cleanup_ret && !ret)
		ret = cleanup_ret;
out_output_bo:
	cleanup_ret = destroy_mapped_bo(queue->fd, &output_bo, error, error_len);
	if (cleanup_ret && !ret)
		ret = cleanup_ret;
out_input_bo:
	cleanup_ret = destroy_mapped_bo(queue->fd, &input_bo, error, error_len);
	if (cleanup_ret && !ret)
		ret = cleanup_ret;
out_context:
	memset(&destroy_context, 0, sizeof(destroy_context));
	destroy_context.handle = context_handle;
	if (ioctl(queue->fd, DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_DESTROY,
		  &destroy_context) < 0 && !ret) {
		ret = -errno;
		set_error(error, error_len,
			  "DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_DESTROY failed", NULL);
	}
	return ret;
}

int apollo_hexagon_load_executable(const char *metadata_path,
						   const char *module_override,
						   struct apollo_hexagon_executable *exe,
					   char *error, size_t error_len)
{
	char module_name[256] = "tiny_cnn_aarch64.vmfb";
	struct stat st;
	FILE *fp;

	memset(exe, 0, sizeof(*exe));
	if (copy_string(exe->entry_point, sizeof(exe->entry_point),
			"tiny_cnn_graph") ||
	    copy_string(exe->expected_output, sizeof(exe->expected_output),
			"1x1x2x2xf32=[[[54 63][90 99]]]") ||
	    copy_string(exe->plugin_path, sizeof(exe->plugin_path),
			"lib/libapollo_iree_hexagon_hal_plugin.so")) {
		set_error(error, error_len, "metadata defaults are too long", NULL);
		return -ENAMETOOLONG;
	}

	if (metadata_path && metadata_path[0]) {
		char line[384];

		fp = fopen(metadata_path, "r");
		if (!fp) {
			set_error(error, error_len, "failed to open metadata %s",
				  metadata_path);
			return -errno;
		}
		while (fgets(line, sizeof(line), fp)) {
			trim_line(line);
			if (strncmp(line, "module=", 7) == 0)
				copy_string(module_name, sizeof(module_name), line + 7);
			else if (strncmp(line, "entry=", 6) == 0)
				copy_string(exe->entry_point, sizeof(exe->entry_point),
					    line + 6);
			else if (strncmp(line, "expected=", 9) == 0)
				copy_string(exe->expected_output,
					    sizeof(exe->expected_output), line + 9);
			else if (strncmp(line, "plugin=", 7) == 0)
				join_relative(exe->plugin_path, sizeof(exe->plugin_path),
					      metadata_path, line + 7);
			else if (strncmp(line, "compiler=", 9) == 0)
				copy_string(exe->compiler_name,
					    sizeof(exe->compiler_name), line + 9);
			else if (strncmp(line, "compiler_artifact=", 18) == 0)
				join_relative(exe->compiler_artifact_path,
					      sizeof(exe->compiler_artifact_path),
					      metadata_path, line + 18);
			else if (strncmp(line, "hexagon_mlir_artifact=", 22) == 0) {
				copy_string(exe->compiler_name,
					    sizeof(exe->compiler_name),
					    "hexagon-mlir");
				join_relative(exe->compiler_artifact_path,
					      sizeof(exe->compiler_artifact_path),
					      metadata_path, line + 22);
			} else if (strncmp(line, "executable_format=", 18) == 0) {
				if (strcmp(line + 18,
					   "apollo-hexagon-apko-v0") == 0)
					exe->executable_format =
						APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0;
			} else if (strncmp(line, "apko=", 5) == 0) {
				join_relative(exe->apko_path,
					      sizeof(exe->apko_path),
					      metadata_path, line + 5);
			} else if (strncmp(line, "apko_abi_version=", 17) == 0) {
				parse_u32(line + 17, &exe->apko_abi_version);
			} else if (strncmp(line, "apko_entry_kind=", 16) == 0) {
				exe->entry_kind = entry_kind_from_name(line + 16);
				if (!exe->entry_kind)
					parse_u32(line + 16, &exe->entry_kind);
			} else if (strncmp(line, "apko_input_bytes=", 17) == 0) {
				parse_u32(line + 17, &exe->input_bytes);
			} else if (strncmp(line, "apko_output_bytes=", 18) == 0) {
				parse_u32(line + 18, &exe->output_bytes);
			}
		}
		fclose(fp);
	}

	if (module_override && module_override[0])
		copy_string(module_name, sizeof(module_name), module_override);

	if (join_relative(exe->module_path, sizeof(exe->module_path),
			metadata_path, module_name)) {
		set_error(error, error_len, "module path is too long", NULL);
		return -ENAMETOOLONG;
	}
	if (!metadata_path || !metadata_path[0]) {
		if (infer_entry_defaults_from_module(exe, exe->module_path)) {
			set_error(error, error_len,
				  "failed to infer executable defaults", NULL);
			return -EINVAL;
		}
	}
	if (stat(exe->module_path, &st)) {
		set_error(error, error_len, "failed to stat module %s",
			  exe->module_path);
		return -errno;
	}
	exe->module_size = (size_t)st.st_size;
	if ((!metadata_path || !metadata_path[0]) && !exe->executable_format) {
		int ret = load_embedded_apko_from_module(exe->module_path, exe,
							 error, error_len);

		if (ret)
			return ret;
	}
	if (exe->plugin_path[0] != '/' && metadata_path && metadata_path[0]) {
		char plugin_name[sizeof(exe->plugin_path)];

		if (copy_string(plugin_name, sizeof(plugin_name), exe->plugin_path) ||
		    join_relative(exe->plugin_path, sizeof(exe->plugin_path),
				  metadata_path, plugin_name)) {
			set_error(error, error_len, "plugin path is too long", NULL);
			return -ENAMETOOLONG;
		}
	}
	if (exe->compiler_artifact_path[0]) {
		if (stat(exe->compiler_artifact_path, &st)) {
			set_error(error, error_len,
				  "failed to stat compiler artifact %s",
				  exe->compiler_artifact_path);
			return -errno;
		}
		exe->compiler_artifact_size = (size_t)st.st_size;
		if (!exe->compiler_name[0])
			copy_string(exe->compiler_name, sizeof(exe->compiler_name),
				    "hexagon-mlir");
	}
	if (exe->executable_format || exe->apko_path[0] || exe->apko_data) {
		if (!exe->executable_format)
			exe->executable_format =
				APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0;
		if (!exe->apko_path[0] && !exe->apko_data) {
			set_error(error, error_len,
				  "APKO executable metadata is missing apko=",
				  NULL);
			return -EINVAL;
		}
		if (!exe->apko_data) {
			if (stat(exe->apko_path, &st)) {
				set_error(error, error_len,
					  "failed to stat APKO %s",
					  exe->apko_path);
				return -errno;
			}
			exe->apko_size = (size_t)st.st_size;
		}
		if (!exe->entry_kind)
			exe->entry_kind = entry_kind_from_name(exe->entry_point);
		if (!exe->input_bytes &&
		    exe->entry_kind == APOLLO_HEXAGON_EXEC_KIND_CNN)
			exe->input_bytes =
				APOLLO_HEXAGON_CNN_INPUT_WORDS * sizeof(uint32_t);
		if (!exe->input_bytes &&
		    exe->entry_kind == APOLLO_HEXAGON_EXEC_KIND_VADD)
			exe->input_bytes =
				APOLLO_HEXAGON_VADD_INPUT_WORDS * sizeof(uint32_t);
		if (!exe->input_bytes &&
		    exe->entry_kind == APOLLO_HEXAGON_EXEC_KIND_MNIST)
			exe->input_bytes =
				APOLLO_HEXAGON_MNIST_INPUT_WORDS *
				sizeof(uint32_t);
		if (!exe->output_bytes &&
		    exe->entry_kind == APOLLO_HEXAGON_EXEC_KIND_CNN)
			exe->output_bytes =
				APOLLO_HEXAGON_CNN_OUTPUT_WORDS * sizeof(uint32_t);
		if (!exe->output_bytes &&
		    exe->entry_kind == APOLLO_HEXAGON_EXEC_KIND_VADD)
			exe->output_bytes =
				APOLLO_HEXAGON_VADD_OUTPUT_WORDS *
				sizeof(uint32_t);
		if (!exe->output_bytes &&
		    exe->entry_kind == APOLLO_HEXAGON_EXEC_KIND_MNIST)
			exe->output_bytes =
				APOLLO_HEXAGON_MNIST_OUTPUT_WORDS *
				sizeof(uint32_t);
	}

	return 0;
}

void apollo_hexagon_unload_executable(struct apollo_hexagon_executable *exe)
{
	if (!exe)
		return;
	free((void *)exe->apko_data);
	exe->apko_data = NULL;
	exe->apko_data_size = 0;
	exe->apko_size = 0;
	exe->apko_embedded = 0;
}

int apollo_hexagon_queue_open(struct apollo_hexagon_queue *queue,
			      const char *device, char *error, size_t error_len)
{
	struct drm_apollo_hexagon_query query;
	struct drm_apollo_hexagon_query_caps caps = { 0 };
	char candidate[sizeof(queue->device_path)];
	const char *selected = device;
	int fd;
	int ret;
	int i;

	memset(queue, 0, sizeof(*queue));
	queue->fd = -1;

	if (!selected || !selected[0])
		selected = getenv("APOLLO_HEXAGON_DEV");

	for (i = 0; i < APOLLO_HEXAGON_ACCEL_SCAN_MAX; i++) {
		if (selected && selected[0]) {
			ret = copy_string(candidate, sizeof(candidate), selected);
		} else {
			ret = snprintf(candidate, sizeof(candidate),
				       "/dev/accel/accel%d", i);
			ret = ret >= 0 && (size_t)ret < sizeof(candidate) ?
			      0 : -ENAMETOOLONG;
		}
		if (ret) {
			set_error(error, error_len,
				  "DRM accel device path is too long", NULL);
			return ret;
		}

		fd = open(candidate, O_RDWR | O_CLOEXEC);
		if (fd < 0) {
			if (selected && selected[0]) {
				set_error(error, error_len,
					  "failed to open DRM accel device %s",
					  candidate);
				return -errno;
			}
			continue;
		}

		memset(&query, 0, sizeof(query));
		if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_QUERY, &query) < 0) {
			ret = -errno;
			close(fd);
			if (selected && selected[0]) {
				set_error(error, error_len,
					  "failed to query Apollo DRM accel device %s",
					  candidate);
				return ret;
			}
			continue;
		}

		memset(&caps, 0, sizeof(caps));
		caps.size = sizeof(caps);
		if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_QUERY_CAPS, &caps) < 0) {
			ret = -errno;
			close(fd);
			if (selected && selected[0]) {
				set_error(error, error_len,
					  "failed to query Apollo DRM accel caps %s",
					  candidate);
				return ret;
			}
			continue;
		}
		ret = validate_query_caps(&caps);
		if (ret) {
			close(fd);
			if (selected && selected[0]) {
				set_error(error, error_len,
					  "Apollo DRM accel caps are incompatible",
					  NULL);
				return ret;
			}
			continue;
		}

		break;
	}

	if (i == APOLLO_HEXAGON_ACCEL_SCAN_MAX) {
		set_error(error, error_len,
			  "failed to discover Apollo DRM accel device %s",
			  "/dev/accel/accel*");
		return -ENOENT;
	}

	ret = copy_string(queue->device_path, sizeof(queue->device_path),
			  candidate);
	if (ret) {
		close(fd);
		set_error(error, error_len, "DRM accel device path is too long",
			  NULL);
		return ret;
	}
	queue->fd = fd;
	queue->device = queue->device_path;
	queue->queue_id = 0;
	queue->queue_count = query.queue_count ? query.queue_count : 1;
	queue->generic_abi_version = caps.generic_abi_version;
	queue->supported_executable_formats = caps.supported_executable_formats;
	queue->max_command_bytes = caps.max_command_bytes;
	queue->max_bindings_per_dispatch = caps.max_bindings_per_dispatch;
	queue->max_queue_depth = caps.max_queue_depth;
	queue->fence_model = caps.fence_model;
	queue->smmu_page_granularity = caps.smmu_page_granularity;
	queue->fault_record_size = caps.fault_record_size;
	return 0;
}

void apollo_hexagon_queue_close(struct apollo_hexagon_queue *queue)
{
	if (queue->fd >= 0)
		close(queue->fd);
	queue->fd = -1;
}

void apollo_hexagon_queue_select(struct apollo_hexagon_queue *queue,
				 uint32_t queue_id)
{
	queue->queue_id = queue_id % queue->queue_count;
}

int apollo_hexagon_queue_submit_cnn(struct apollo_hexagon_queue *queue,
				    struct apollo_hexagon_command_buffer *cmd,
				    struct apollo_hexagon_fence *fence,
				    char *error, size_t error_len)
{
	struct drm_apollo_hexagon_cnn_job job;
	int ret;

	memset(&job, 0, sizeof(job));
	memcpy(job.input, cmd->input, sizeof(job.input));
	job.queue_id = queue->queue_id;
	ret = ioctl(queue->fd, DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_CNN, &job);
	if (ret < 0) {
		set_error(error, error_len,
			  "DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_CNN failed",
			  NULL);
		return -errno;
	}

	memcpy(cmd->output, job.output, sizeof(cmd->output));
	cmd->status = job.status;
	fence->status = job.status;
	fence->signaled = 1;
	fence->queue_id = job.queue_id;
	fence->fence_seq = job.fence_seq;
	return 0;
}

int apollo_hexagon_queue_submit_vadd(struct apollo_hexagon_queue *queue,
				     struct apollo_hexagon_vadd_command_buffer *cmd,
				     struct apollo_hexagon_fence *fence,
				     char *error, size_t error_len)
{
	struct drm_apollo_hexagon_vadd_job job;
	int ret;

	memset(&job, 0, sizeof(job));
	memcpy(job.lhs, cmd->lhs, sizeof(job.lhs));
	memcpy(job.rhs, cmd->rhs, sizeof(job.rhs));
	job.queue_id = queue->queue_id;
	ret = ioctl(queue->fd, DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_VADD, &job);
	if (ret < 0) {
		set_error(error, error_len,
			  "DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_VADD failed",
			  NULL);
		return -errno;
	}

	memcpy(cmd->output, job.output, sizeof(cmd->output));
	cmd->status = job.status;
	fence->status = job.status;
	fence->signaled = 1;
	fence->queue_id = job.queue_id;
	fence->fence_seq = job.fence_seq;
	return 0;
}

int apollo_hexagon_queue_submit_apko(
	struct apollo_hexagon_queue *queue,
	const struct apollo_hexagon_executable *exe, const void *input,
	size_t input_bytes, void *output, size_t output_bytes,
	struct apollo_hexagon_fence *fence, char *error, size_t error_len)
{
	struct drm_apollo_hexagon_exec_destroy destroy;
	struct drm_apollo_hexagon_exec_create create;
	struct drm_apollo_hexagon_submit submit;
	void *apko_data = NULL;
	const void *create_data;
	size_t apko_size = 0;
	uint32_t payload_opcode = 0;
	uint32_t code_words = 0;
	uint32_t entry_word = 0;
	int ret;

	if ((!exe->apko_path[0] && !exe->apko_data) ||
	    exe->executable_format != APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0) {
		set_error(error, error_len,
			  "missing apollo-hexagon-apko-v0 executable metadata",
			  NULL);
		return -EINVAL;
	}

	if (exe->apko_data && exe->apko_data_size) {
		create_data = exe->apko_data;
		apko_size = exe->apko_data_size;
	} else {
		ret = read_whole_file(exe->apko_path, &apko_data, &apko_size,
				      error, error_len);
		if (ret)
			return ret;
		create_data = apko_data;
	}

	memset(&create, 0, sizeof(create));
	create.size = sizeof(create);
	create.data_ptr = (uint64_t)(uintptr_t)create_data;
	create.data_size = (uint32_t)apko_size;
	ret = ioctl(queue->fd, DRM_IOCTL_APOLLO_HEXAGON_EXEC_CREATE, &create);
	if (ret < 0) {
		ret = -errno;
		set_error(error, error_len,
			  "DRM_IOCTL_APOLLO_HEXAGON_EXEC_CREATE failed",
			  NULL);
		goto out_free;
	}

	if (create.executable_format != APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0 ||
	    create.abi_version != APOLLO_HEXAGON_APKO_ABI_VERSION ||
	    input_bytes != create.input_bytes ||
	    output_bytes != create.output_bytes) {
		ret = -EINVAL;
		set_error(error, error_len,
			  "APKO executable ABI does not match command buffers",
			  NULL);
		goto out_destroy;
	}

	if ((create.entry_kind == APOLLO_HEXAGON_EXEC_KIND_CNN ||
	     create.entry_kind == APOLLO_HEXAGON_EXEC_KIND_VADD ||
	     create.entry_kind == APOLLO_HEXAGON_EXEC_KIND_MNIST) &&
	    queue->max_command_bytes >= APOLLO_HEXAGON_CMDQ_SUBMIT_MAX_BYTES &&
	    queue->max_bindings_per_dispatch >= 2) {
		ret = read_apko_payload_program(create_data, apko_size,
						create.entry_kind,
						&payload_opcode,
						&code_words,
						&entry_word);
		if (ret) {
			if (ret != -ENODATA) {
				set_error(error, error_len,
					  "APKO payload descriptor is invalid",
					  NULL);
				goto out_destroy;
			}
		} else {
			ret = apollo_hexagon_queue_submit_apko_cmdq(
				queue, create.handle, create.entry_kind,
				payload_opcode, code_words, entry_word, input,
				input_bytes, output, output_bytes, fence, error,
				error_len);
			goto out_destroy;
		}
	}

	memset(&submit, 0, sizeof(submit));
	submit.size = sizeof(submit);
	submit.executable_handle = create.handle;
	submit.queue_id = queue->queue_id;
	submit.input_ptr = (uint64_t)(uintptr_t)input;
	submit.output_ptr = (uint64_t)(uintptr_t)output;
	submit.input_bytes = (uint32_t)input_bytes;
	submit.output_bytes = (uint32_t)output_bytes;
	ret = ioctl(queue->fd, DRM_IOCTL_APOLLO_HEXAGON_SUBMIT, &submit);
	if (ret < 0) {
		ret = -errno;
		set_error(error, error_len,
			  "DRM_IOCTL_APOLLO_HEXAGON_SUBMIT failed", NULL);
		goto out_destroy;
	}

	fence->status = submit.status;
	fence->signaled = 1;
	fence->queue_id = submit.queue_id;
	fence->fence_seq = submit.fence_seq;
	ret = 0;

out_destroy:
	memset(&destroy, 0, sizeof(destroy));
	destroy.handle = create.handle;
	if (ioctl(queue->fd, DRM_IOCTL_APOLLO_HEXAGON_EXEC_DESTROY,
		  &destroy) < 0 && !ret) {
		ret = -errno;
		set_error(error, error_len,
			  "DRM_IOCTL_APOLLO_HEXAGON_EXEC_DESTROY failed",
			  NULL);
	}
out_free:
	free(apko_data);
	return ret;
}

int apollo_hexagon_queue_submit_dma_stress(struct apollo_hexagon_queue *queue,
					   uint32_t bytes, uint32_t seed,
					   uint32_t *checksum,
					   struct apollo_hexagon_fence *fence,
					   char *error, size_t error_len)
{
	struct drm_apollo_hexagon_dma_stress_job job;
	int ret;

	memset(&job, 0, sizeof(job));
	job.bytes = bytes;
	job.segment_bytes = bytes / APOLLO_HEXAGON_DMA_STRESS_SEGMENTS;
	job.seed = seed;
	job.queue_id = queue->queue_id;
	ret = ioctl(queue->fd, DRM_IOCTL_APOLLO_HEXAGON_DMA_STRESS, &job);
	if (ret < 0) {
		set_error(error, error_len,
			  "DRM_IOCTL_APOLLO_HEXAGON_DMA_STRESS failed",
			  NULL);
		return -errno;
	}

	*checksum = job.checksum;
	fence->status = job.status;
	fence->signaled = 1;
	fence->queue_id = job.queue_id;
	fence->fence_seq = job.fence_seq;
	return 0;
}
