// SPDX-License-Identifier: MIT
#include "apollo_iree_hexagon_hal.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>

#define APOLLO_HEXAGON_ACCEL_SCAN_MAX 256

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
	if (stat(exe->module_path, &st)) {
		set_error(error, error_len, "failed to stat module %s",
			  exe->module_path);
		return -errno;
	}
	exe->module_size = (size_t)st.st_size;
	if (exe->plugin_path[0] != '/' && metadata_path && metadata_path[0]) {
		char plugin_name[sizeof(exe->plugin_path)];

		if (copy_string(plugin_name, sizeof(plugin_name), exe->plugin_path) ||
		    join_relative(exe->plugin_path, sizeof(exe->plugin_path),
				  metadata_path, plugin_name)) {
			set_error(error, error_len, "plugin path is too long", NULL);
			return -ENAMETOOLONG;
		}
	}

	return 0;
}

int apollo_hexagon_queue_open(struct apollo_hexagon_queue *queue,
			      const char *device, char *error, size_t error_len)
{
	struct drm_apollo_hexagon_query query;
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
		if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_QUERY, &query) == 0)
			break;

		ret = -errno;
		close(fd);
		if (selected && selected[0]) {
			set_error(error, error_len,
				  "failed to query Apollo DRM accel device %s",
				  candidate);
			return ret;
		}
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
