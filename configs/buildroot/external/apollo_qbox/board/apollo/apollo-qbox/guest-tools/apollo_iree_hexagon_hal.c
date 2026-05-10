// SPDX-License-Identifier: MIT
#include "apollo_iree_hexagon_hal.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>

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
	memset(queue, 0, sizeof(*queue));
	queue->fd = open(device, O_RDWR | O_CLOEXEC);
	if (queue->fd < 0) {
		set_error(error, error_len, "failed to open device %s", device);
		return -errno;
	}
	queue->device = device;
	queue->queue_id = 0;
	queue->queue_count = 2;
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
	struct apollo_hexagon_cnn_job job;
	int ret;

	memset(&job, 0, sizeof(job));
	memcpy(job.input, cmd->input, sizeof(job.input));
	job.queue_id = queue->queue_id;
	ret = ioctl(queue->fd, APOLLO_HEXAGON_IOC_SUBMIT_CNN, &job);
	if (ret < 0) {
		set_error(error, error_len, "APOLLO_HEXAGON_IOC_SUBMIT_CNN failed",
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
	struct apollo_hexagon_dma_stress_job job;
	int ret;

	memset(&job, 0, sizeof(job));
	job.bytes = bytes;
	job.segment_bytes = bytes / APOLLO_HEXAGON_DMA_STRESS_SEGMENTS;
	job.seed = seed;
	job.queue_id = queue->queue_id;
	ret = ioctl(queue->fd, APOLLO_HEXAGON_IOC_DMA_STRESS, &job);
	if (ret < 0) {
		set_error(error, error_len, "APOLLO_HEXAGON_IOC_DMA_STRESS failed",
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
